from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.borrow_request import BorrowRequest
from test_items import ORIGIN, item_payload, register_and_login

PAYLOAD = {"requested_start_at": "2030-01-01T10:00:00+08:00", "expected_return_at": "2030-01-03T10:00:00+08:00", "note": "  课程借用  "}


@pytest.fixture
def actors(client, test_app):
    register_and_login(client, "BORROW_OWNER_P4", "物主同学")
    with TestClient(test_app) as borrower, TestClient(test_app) as other:
        register_and_login(borrower, "BORROW_USER_P4", "借用同学")
        register_and_login(other, "BORROW_OTHER_P4", "另一同学")
        item = client.post("/api/items", headers=ORIGIN, json=item_payload("borrow")).json()
        yield client, borrower, other, item


def request(borrower, item, payload=PAYLOAD):
    return borrower.post(f"/api/items/{item['id']}/borrow-requests", headers=ORIGIN, json=payload)


def action(client, borrow_id, name, headers=ORIGIN):
    return client.post(f"/api/borrows/{borrow_id}/{name}", headers=headers)


def availability(client, item):
    return client.get(f"/api/items/{item['id']}").json()["availability"]


def test_dual_confirmation_return_history_and_repeated_borrowing(actors):
    owner, borrower, other, item = actors
    created = request(borrower, item)
    assert created.status_code == 201
    borrow = created.json(); borrow_id = borrow["id"]
    assert borrow["status"] == "pending" and borrow["note"] == "课程借用"
    assert borrow["requested_start_at"] == "2030-01-01T02:00:00Z"
    assert borrow["expected_return_at"] == "2030-01-03T02:00:00Z"
    assert request(borrower, item).status_code == 409
    assert action(borrower, borrow_id, "confirm-handover").status_code == 409
    assert action(borrower, borrow_id, "confirm-return").status_code == 409
    assert action(owner, borrow_id, "approve").json()["status"] == "approved"
    assert availability(borrower, item) == "reserved"
    assert request(other, item).status_code == 409
    first = action(borrower, borrow_id, "confirm-handover").json()
    assert first["status"] == "approved" and first["borrowed_at"] is None
    assert action(borrower, borrow_id, "confirm-handover").json() == first
    for actor in (owner, borrower):
        assert action(actor, borrow_id, "cancel").status_code == 409
    assert action(owner, borrow_id, "confirm-return").status_code == 409
    borrowed = action(owner, borrow_id, "confirm-handover").json()
    assert borrowed["status"] == "borrowed" and borrowed["borrowed_at"]
    assert availability(borrower, item) == "borrowed"
    assert action(owner, borrow_id, "cancel").status_code == 409
    first_return = action(owner, borrow_id, "confirm-return").json()
    assert first_return["status"] == "return_pending" and first_return["completed_at"] is None
    assert action(owner, borrow_id, "confirm-return").json() == first_return
    assert availability(borrower, item) == "return_pending"
    assert request(other, item).status_code == 409
    assert action(borrower, borrow_id, "cancel").status_code == 409
    completed = action(borrower, borrow_id, "confirm-return").json()
    assert completed["status"] == "completed" and completed["completed_at"]
    for actor in (owner, borrower):
        assert action(actor, borrow_id, "confirm-return").json() == completed
        assert action(actor, borrow_id, "confirm-handover").json() == completed
    assert availability(borrower, item) == "available"
    # The same user and item can start a new cycle; completed must not block either index.
    next_borrow = request(borrower, item)
    assert next_borrow.status_code == 201 and next_borrow.json()["id"] != borrow_id
    assert action(owner, next_borrow.json()["id"], "approve").json()["status"] == "approved"
    history = borrower.get("/api/borrows/mine?role=borrower").json()
    assert history["total"] == 2
    assert next(row for row in history["borrows"] if row["id"] == borrow_id) == completed


def test_invalid_items_time_order_and_free_only_fields(actors):
    owner, borrower, _, item = actors
    assert item["price_cents"] is None
    assert request(owner, item).status_code == 409
    sale = owner.post("/api/items", headers=ORIGIN, json=item_payload()).json()
    assert request(borrower, sale).status_code == 409
    invalid_payloads = [
        PAYLOAD | {"expected_return_at": PAYLOAD["requested_start_at"]},
        PAYLOAD | {"requested_start_at": "2030-01-05T10:00:00+08:00"},
        PAYLOAD | {"requested_start_at": "not-a-date"},
        PAYLOAD | {"requested_start_at": "2030-01-01T10:00:00"},
        PAYLOAD | {"requested_start_at": 1234567890},
        *[PAYLOAD | {field: 100} for field in ("rent_cents", "deposit_cents", "fee_cents", "owner_id", "borrower_id")],
    ]
    for payload in invalid_payloads:
        assert request(borrower, item, payload).status_code == 422
    created = request(borrower, item).json()
    assert not {"price_cents", "price_cents_snapshot", "rent_cents", "deposit_cents", "fee_cents"}.intersection(created)
    assert action(borrower, created["id"], "cancel").status_code == 200
    assert owner.delete(f"/api/items/{item['id']}", headers=ORIGIN).status_code == 200
    assert request(borrower, item).status_code == 409


def test_auth_origin_roles_and_private_lists(actors, test_app):
    owner, borrower, other, item = actors
    borrow_id = request(borrower, item).json()["id"]
    names = ("approve", "reject", "cancel", "confirm-handover", "confirm-return")
    with TestClient(test_app) as anonymous:
        assert anonymous.get("/api/borrows/mine").status_code == 401
        assert request(anonymous, item).status_code == 401
        for name in names:
            assert action(anonymous, borrow_id, name).status_code == 401
    for headers in ({}, {"Origin": "https://example.com"}):
        assert borrower.post(f"/api/items/{item['id']}/borrow-requests", headers=headers, json=PAYLOAD).status_code == 403
        for name in names:
            assert action(owner, borrow_id, name, headers).status_code == 403
    for name in names:
        assert action(other, borrow_id, name).status_code == 404
    assert action(borrower, borrow_id, "approve").status_code == 403
    assert action(borrower, borrow_id, "reject").status_code == 403
    assert action(owner, borrow_id, "cancel").status_code == 403
    assert other.get("/api/borrows/mine").json()["borrows"] == []
    for actor, role in ((owner, "owner"), (borrower, "borrower")):
        listing = actor.get(f"/api/borrows/mine?role={role}").json()
        assert listing["total"] == 1 and listing["borrows"][0]["id"] == borrow_id
        for secret in ("student_no", "student_no_masked", "password_hash", "token_hash", "BORROW_OWNER_P4", "BORROW_USER_P4"):
            assert secret not in str(listing)
    assert borrower.get("/api/borrows/mine?role=owner").json()["total"] == 0


def test_rejection_and_pending_cancellation_keep_history(actors):
    owner, borrower, _, item = actors
    rejected = request(borrower, item).json()
    assert action(owner, rejected["id"], "reject").json()["status"] == "rejected"
    assert action(owner, rejected["id"], "approve").status_code == 409
    pending = request(borrower, item).json()
    canceled = action(borrower, pending["id"], "cancel").json()
    assert canceled["status"] == "canceled"
    assert action(borrower, pending["id"], "cancel").json() == canceled
    assert availability(borrower, item) == "available"
    assert borrower.get("/api/borrows/mine").json()["total"] == 2


@pytest.mark.parametrize("canceler", ["owner", "borrower"])
def test_cancel_unconfirmed_approval_releases_item(actors, canceler):
    owner, borrower, other, item = actors
    first = request(borrower, item).json()
    second = request(other, item).json()
    assert action(owner, first["id"], "approve").status_code == 200
    assert other.get("/api/borrows/mine").json()["borrows"][0]["status"] == "rejected"
    assert action(owner, second["id"], "approve").status_code == 409
    actor = owner if canceler == "owner" else borrower
    assert action(actor, first["id"], "cancel").json()["status"] == "canceled"
    assert availability(borrower, item) == "available"
    assert request(other, item).status_code == 201


def test_active_borrow_blocks_mode_and_withdraw_but_allows_description(actors):
    owner, borrower, _, item = actors
    borrow_id = request(borrower, item).json()["id"]
    for state in ("pending", "approved", "borrowed", "return_pending"):
        assert owner.patch(f"/api/items/{item['id']}", headers=ORIGIN, json={"mode": "sale", "price_cents": 1200}).status_code == 409
        assert owner.delete(f"/api/items/{item['id']}", headers=ORIGIN).status_code == 409
        assert owner.patch(f"/api/items/{item['id']}", headers=ORIGIN, json={"description": "补充借用说明", "interest_tags": ["学习"]}).status_code == 200
        if state == "pending":
            assert action(owner, borrow_id, "approve").status_code == 200
        elif state == "approved":
            assert action(owner, borrow_id, "confirm-handover").status_code == 200
            assert action(borrower, borrow_id, "confirm-handover").json()["status"] == "borrowed"
        elif state == "borrowed":
            assert action(borrower, borrow_id, "confirm-return").json()["status"] == "return_pending"
    assert action(owner, borrow_id, "confirm-return").json()["status"] == "completed"
    sale = owner.patch(f"/api/items/{item['id']}", headers=ORIGIN, json={"mode": "sale", "price_cents": 1200})
    assert sale.status_code == 200 and sale.json()["availability"] == "available"
    # Historical borrowing must not prevent a later sale after an allowed mode change.
    trade = borrower.post(f"/api/items/{item['id']}/trade-intents", headers=ORIGIN, json={})
    assert trade.status_code == 201
    assert owner.post(f"/api/trades/{trade.json()['id']}/accept", headers=ORIGIN).status_code == 200


def test_concurrent_approval_and_unique_index_protect_one_active_borrow(actors, test_app):
    owner, borrower, other, item = actors
    first, second = request(borrower, item).json(), request(other, item).json()
    barrier = Barrier(2)

    def approve_together(borrow_id):
        with TestClient(test_app) as worker:
            worker.cookies.update(owner.cookies)
            barrier.wait(timeout=5)
            return action(worker, borrow_id, "approve").status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(approve_together, (first["id"], second["id"])))
    assert sorted(results) == [200, 409]
    with test_app.state.session_factory() as db:
        borrows = db.scalars(select(BorrowRequest).where(BorrowRequest.item_id == item["id"])).all()
        assert sorted(borrow.status for borrow in borrows) == ["approved", "rejected"]
        rejected = next(borrow for borrow in borrows if borrow.status == "rejected")
        db.add(BorrowRequest(item_id=item["id"], owner_id=rejected.owner_id, borrower_id=rejected.borrower_id,
                             requested_start_at=datetime(2030, 1, 1, tzinfo=UTC), expected_return_at=datetime(2030, 1, 2, tzinfo=UTC), status="approved"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
