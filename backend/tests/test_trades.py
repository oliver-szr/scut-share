from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.trade_intent import TradeIntent
from test_items import ORIGIN, item_payload, register_and_login


@pytest.fixture
def actors(client, test_app):
    register_and_login(client, "TRADE_SELLER", "卖家同学")
    with TestClient(test_app) as buyer, TestClient(test_app) as other:
        register_and_login(buyer, "TRADE_BUYER", "买家同学")
        register_and_login(other, "TRADE_OTHER", "另一同学")
        item = client.post("/api/items", headers=ORIGIN, json=item_payload()).json()
        yield client, buyer, other, item


def intent(buyer, item, **body):
    return buyer.post(f"/api/items/{item['id']}/trade-intents", headers=ORIGIN, json=body)


def action(client, trade_id, name, headers=ORIGIN):
    return client.post(f"/api/trades/{trade_id}/{name}", headers=headers)


def test_two_users_complete_sale_with_idempotent_confirmation(actors):
    seller, buyer, other, item = actors
    created = intent(buyer, item, note="  周五线下交接  ")
    assert created.status_code == 201
    trade = created.json()
    assert trade["status"] == "pending" and trade["note"] == "周五线下交接"
    assert trade["price_cents_snapshot"] == item["price_cents"]
    assert intent(buyer, item).status_code == 409
    assert action(buyer, trade["id"], "accept").status_code == 403
    assert action(buyer, trade["id"], "confirm").status_code == 409
    assert action(seller, trade["id"], "accept").json()["status"] == "reserved"
    assert buyer.get(f"/api/items/{item['id']}").json()["availability"] == "reserved"
    assert intent(other, item).status_code == 409
    first = action(buyer, trade["id"], "confirm").json()
    assert first["status"] == "reserved" and first["completed_at"] is None
    assert action(buyer, trade["id"], "confirm").json()["buyer_confirmed_at"] == first["buyer_confirmed_at"]
    assert action(buyer, trade["id"], "cancel").status_code == 409
    assert action(seller, trade["id"], "cancel").status_code == 409
    completed = action(seller, trade["id"], "confirm").json()
    assert completed["status"] == "completed"
    assert all(completed[field] for field in ("buyer_confirmed_at", "seller_confirmed_at", "completed_at"))
    assert action(seller, trade["id"], "confirm").json() == completed
    assert action(buyer, trade["id"], "confirm").json() == completed
    assert intent(other, item).status_code == 409
    assert buyer.get(f"/api/items/{item['id']}").json()["availability"] == "sold"
    assert buyer.get("/api/items").json()["items"][0]["availability"] == "sold"
    assert seller.patch(f"/api/items/{item['id']}", headers=ORIGIN, json={"mode": "borrow"}).status_code == 409
    assert seller.delete(f"/api/items/{item['id']}", headers=ORIGIN).status_code == 409
    assert action(seller, trade["id"], "cancel").status_code == 409


def test_invalid_items_and_anonymous_requests(actors, test_app):
    seller, buyer, _, item = actors
    path = f"/api/items/{item['id']}/trade-intents"
    with TestClient(test_app) as anonymous:
        assert anonymous.post(path, headers=ORIGIN, json={}).status_code == 401
        assert anonymous.get("/api/trades/mine").status_code == 401
    assert intent(seller, item).status_code == 409
    borrowed = seller.post("/api/items", headers=ORIGIN, json=item_payload("borrow")).json()
    assert intent(buyer, borrowed).status_code == 409
    assert seller.delete(f"/api/items/{item['id']}", headers=ORIGIN).status_code == 200
    assert intent(buyer, item).status_code == 409
    assert intent(buyer, item, buyer_id=999).status_code == 422


def test_private_data_origin_and_participant_permissions(actors):
    seller, buyer, other, item = actors
    trade = intent(buyer, item).json()
    for headers in ({}, {"Origin": "https://example.com"}):
        assert buyer.post(f"/api/items/{item['id']}/trade-intents", headers=headers, json={}).status_code == 403
        for name in ("accept", "reject", "cancel", "confirm"):
            assert action(seller, trade["id"], name, headers).status_code == 403
    for name in ("accept", "reject", "cancel", "confirm"):
        assert action(other, trade["id"], name).status_code == 404
    assert other.get("/api/trades/mine").json()["trades"] == []
    for participant, role in ((seller, "seller"), (buyer, "buyer")):
        listing = participant.get(f"/api/trades/mine?role={role}").json()
        assert listing["total"] == 1 and listing["trades"][0]["id"] == trade["id"]
        for private_key in ("student_no", "student_no_masked", "password_hash", "token_hash", "TRADE_BUYER", "TRADE_SELLER"):
            assert private_key not in str(listing)
    assert buyer.get("/api/trades/mine?role=seller").json()["total"] == 0
    assert action(buyer, trade["id"], "reject").status_code == 403
    assert action(seller, trade["id"], "cancel").status_code == 403


def test_reject_cancel_and_price_snapshot_survive_later_edit(actors):
    seller, buyer, _, item = actors
    rejected = intent(buyer, item).json()
    assert action(seller, rejected["id"], "reject").json()["status"] == "rejected"
    assert action(seller, rejected["id"], "accept").status_code == 409
    pending = intent(buyer, item).json()
    assert action(buyer, pending["id"], "cancel").json()["status"] == "canceled"
    assert action(buyer, pending["id"], "cancel").json()["status"] == "canceled"
    assert seller.patch(f"/api/items/{item['id']}", headers=ORIGIN, json={"price_cents": 2300}).status_code == 200
    assert all(trade["price_cents_snapshot"] == 1200 for trade in buyer.get("/api/trades/mine").json()["trades"])
    assert intent(buyer, item).json()["price_cents_snapshot"] == 2300


@pytest.mark.parametrize("canceler", ["buyer", "seller"])
def test_unconfirmed_reservation_can_be_canceled_and_purchased_again(actors, canceler):
    seller, buyer, other, item = actors
    first = intent(buyer, item).json()
    second = intent(other, item).json()
    assert action(seller, first["id"], "accept").status_code == 200
    assert other.get("/api/trades/mine").json()["trades"][0]["status"] == "rejected"
    assert action(seller, second["id"], "accept").status_code == 409
    actor = buyer if canceler == "buyer" else seller
    assert action(actor, first["id"], "cancel").json()["status"] == "canceled"
    assert buyer.get(f"/api/items/{item['id']}").json()["availability"] == "available"
    assert intent(other, item).status_code == 201


def test_active_trades_block_destructive_item_edits(actors):
    seller, buyer, _, item = actors
    trade = intent(buyer, item).json()
    for status in ("pending", "reserved"):
        for changes in ({"price_cents": 2300}, {"mode": "borrow"}):
            assert seller.patch(f"/api/items/{item['id']}", headers=ORIGIN, json=changes).status_code == 409
        assert seller.delete(f"/api/items/{item['id']}", headers=ORIGIN).status_code == 409
        assert seller.patch(f"/api/items/{item['id']}", headers=ORIGIN, json={"title": "描述可以修改", "price_cents": 1200}).status_code == 200
        if status == "pending":
            assert action(seller, trade["id"], "accept").status_code == 200
    assert action(seller, trade["id"], "cancel").status_code == 200
    assert seller.patch(f"/api/items/{item['id']}", headers=ORIGIN, json={"price_cents": 2300}).status_code == 200
    assert seller.delete(f"/api/items/{item['id']}", headers=ORIGIN).status_code == 200
    assert seller.patch(f"/api/items/{item['id']}", headers=ORIGIN, json={"title": "下架后编辑"}).status_code == 200


def test_concurrent_accepts_and_database_constraint_allow_only_one_reservation(actors, test_app):
    seller, buyer, other, item = actors
    first, second = intent(buyer, item).json(), intent(other, item).json()
    barrier = Barrier(2)

    def accept_at_once(trade_id):
        with TestClient(test_app) as worker:
            worker.cookies.update(seller.cookies)
            barrier.wait(timeout=5)
            return action(worker, trade_id, "accept").status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(accept_at_once, (first["id"], second["id"])))
    assert sorted(results) == [200, 409]
    with test_app.state.session_factory() as db:
        trades = db.scalars(select(TradeIntent).where(TradeIntent.item_id == item["id"])).all()
        assert sorted(trade.status for trade in trades) == ["rejected", "reserved"]
        rejected = next(trade for trade in trades if trade.status == "rejected")
        # Even a write bypassing the API cannot insert a second reservation.
        db.add(TradeIntent(item_id=item["id"], buyer_id=rejected.buyer_id, seller_id=rejected.seller_id,
                           price_cents_snapshot=1200, status="reserved"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
