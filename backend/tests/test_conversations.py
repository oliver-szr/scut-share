from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.conversation import Conversation, Message
from test_borrows import PAYLOAD
from test_items import ORIGIN, item_payload, register_and_login


@pytest.fixture
def actors(client, test_app):
    register_and_login(client, "CHAT_OWNER", "物主同学")
    with TestClient(test_app) as buyer, TestClient(test_app) as other:
        register_and_login(buyer, "CHAT_BUYER", "买方同学")
        register_and_login(other, "CHAT_OTHER", "其他同学")
        item = client.post("/api/items", headers=ORIGIN, json=item_payload()).json()
        yield client, buyer, other, item


def sale_chat(actor, item):
    return actor.post(f"/api/items/{item['id']}/conversations", headers=ORIGIN, json={})


def send(actor, conversation_id, content, **extra):
    return actor.post(f"/api/conversations/{conversation_id}/messages", headers=ORIGIN, json={"content": content, **extra})


def borrow_fixture(owner, buyer):
    item = owner.post("/api/items", headers=ORIGIN, json=item_payload("borrow")).json()
    borrow = buyer.post(f"/api/items/{item['id']}/borrow-requests", headers=ORIGIN, json=PAYLOAD).json()
    return item, borrow, f"/api/borrows/{borrow['id']}"


def test_sale_consultation_reused_without_trade_and_other_buyers_isolated(actors):
    owner, buyer, other, item = actors
    created = sale_chat(buyer, item)
    assert created.status_code == 200
    first = created.json()
    assert first["context_type"] == "sale_item" and first["other_user"]["nickname"] == "物主同学"
    assert first["borrow_request_id"] is None and first["last_message"] is None
    assert sale_chat(buyer, item).json()["id"] == first["id"]
    second = sale_chat(other, item).json()
    assert second["id"] != first["id"]
    assert send(buyer, first["id"], "买方的私密问题").status_code == 201
    assert other.get(f"/api/conversations/{first['id']}/messages").status_code == 404
    assert buyer.get(f"/api/conversations/{second['id']}/messages").status_code == 404
    assert owner.get("/api/conversations").json()["total"] == 2
    assert buyer.get("/api/conversations").json()["total"] == 1
    assert other.get("/api/conversations").json()["conversations"][0]["last_message"] is None
    assert buyer.get("/api/trades/mine").json()["total"] == 0


def test_sale_creation_eligibility_and_existing_chat_after_withdrawal(actors):
    owner, buyer, other, item = actors
    assert sale_chat(owner, item).status_code == 409
    borrow_item = owner.post("/api/items", headers=ORIGIN, json=item_payload("borrow")).json()
    assert sale_chat(buyer, borrow_item).status_code == 409
    chat = sale_chat(buyer, item).json()
    assert owner.delete(f"/api/items/{item['id']}", headers=ORIGIN).status_code == 200
    assert sale_chat(other, item).status_code == 409
    assert sale_chat(buyer, item).json()["id"] == chat["id"]
    assert send(owner, chat["id"], "商品已下架，原会话保留").status_code == 201
    assert buyer.get(f"/api/conversations/{chat['id']}/messages").json()["messages"][0]["content"] == "商品已下架，原会话保留"


def test_trade_contact_uses_record_participants_and_survives_completion(actors):
    owner, buyer, other, item = actors
    trade = buyer.post(f"/api/items/{item['id']}/trade-intents", headers=ORIGIN, json={}).json()
    path = f"/api/trades/{trade['id']}"
    assert other.post(path + "/conversation", headers=ORIGIN).status_code == 404
    assert owner.post(path + "/accept", headers=ORIGIN).status_code == 200
    assert sale_chat(other, item).status_code == 409
    # The reserved buyer can still open the record's chat without an arbitrary target ID.
    chat = owner.post(path + "/conversation", headers=ORIGIN, json={}).json()
    assert chat["other_user"]["id"] == trade["buyer_id"]
    assert buyer.post(path + "/conversation", headers=ORIGIN).json()["id"] == chat["id"]
    assert sale_chat(buyer, item).json()["id"] == chat["id"]
    assert send(buyer, chat["id"], "约好线下交付").status_code == 201
    assert buyer.get("/api/trades/mine").json()["trades"][0]["status"] == "reserved"
    assert buyer.post(path + "/confirm", headers=ORIGIN).json()["status"] == "reserved"
    assert owner.post(path + "/confirm", headers=ORIGIN).json()["status"] == "completed"
    assert buyer.get(f"/api/items/{item['id']}").json()["availability"] == "sold"
    assert sale_chat(other, item).status_code == 409
    assert owner.post(path + "/conversation", headers=ORIGIN).json()["id"] == chat["id"]
    assert send(owner, chat["id"], "谢谢，已成交").status_code == 201


def test_borrow_chat_requires_approval_and_preserves_each_cycle(actors):
    owner, buyer, other, _ = actors
    item, borrow, path = borrow_fixture(owner, buyer)
    assert buyer.post(path + "/conversation", headers=ORIGIN).status_code == 409
    assert other.post(path + "/conversation", headers=ORIGIN).status_code == 404
    assert owner.post(path + "/reject", headers=ORIGIN).status_code == 200
    assert buyer.post(path + "/conversation", headers=ORIGIN).status_code == 409
    borrow = buyer.post(f"/api/items/{item['id']}/borrow-requests", headers=ORIGIN, json=PAYLOAD).json()
    path = f"/api/borrows/{borrow['id']}"
    assert owner.post(path + "/approve", headers=ORIGIN).status_code == 200
    chat = buyer.post(path + "/conversation", headers=ORIGIN).json()
    assert chat["context_type"] == "borrow_request" and chat["borrow_request_id"] == borrow["id"]
    assert owner.post(path + "/conversation", headers=ORIGIN).json()["id"] == chat["id"]
    assert send(owner, chat["id"], "在教学楼交接").status_code == 201
    assert buyer.get("/api/borrows/mine").json()["borrows"][0]["status"] == "approved"
    for action, status in (("confirm-handover", "borrowed"), ("confirm-return", "completed")):
        assert buyer.post(path + "/" + action, headers=ORIGIN).status_code == 200
        if action == "confirm-return":
            assert buyer.post(path + "/conversation", headers=ORIGIN).json()["id"] == chat["id"]
        assert owner.post(path + "/" + action, headers=ORIGIN).json()["status"] == status
        assert buyer.post(path + "/conversation", headers=ORIGIN).json()["id"] == chat["id"]
    assert send(buyer, chat["id"], "已归还，感谢分享").status_code == 201
    next_borrow = buyer.post(f"/api/items/{item['id']}/borrow-requests", headers=ORIGIN, json=PAYLOAD).json()
    next_path = f"/api/borrows/{next_borrow['id']}"
    assert owner.post(next_path + "/approve", headers=ORIGIN).status_code == 200
    assert buyer.post(next_path + "/conversation", headers=ORIGIN).json()["id"] != chat["id"]


def test_canceled_approved_borrow_keeps_existing_history(actors):
    owner, buyer, _, _ = actors
    _, _, path = borrow_fixture(owner, buyer)
    owner.post(path + "/approve", headers=ORIGIN)
    chat = buyer.post(path + "/conversation", headers=ORIGIN).json()
    assert buyer.post(path + "/cancel", headers=ORIGIN).status_code == 200
    assert buyer.post(path + "/conversation", headers=ORIGIN).status_code == 409
    assert send(owner, chat["id"], "这次取消，历史仍在").status_code == 201
    assert buyer.get(f"/api/conversations/{chat['id']}/messages").status_code == 200


def test_anonymous_origin_spoofing_and_private_data(actors, test_app):
    owner, buyer, other, item = actors
    chat = sale_chat(buyer, item).json(); path = f"/api/conversations/{chat['id']}"
    with TestClient(test_app) as anonymous:
        assert sale_chat(anonymous, item).status_code == 401
        for route in ("/api/conversations", path, path + "/messages"):
            assert anonymous.get(route).status_code == 401
        assert send(anonymous, chat["id"], "匿名消息").status_code == 401
    for headers in ({}, {"Origin": "https://untrusted.example"}):
        assert buyer.post(f"/api/items/{item['id']}/conversations", headers=headers).status_code == 403
        assert buyer.post(path + "/messages", headers=headers, json={"content": "消息"}).status_code == 403
        _, _, borrow_path = borrow_fixture(owner, buyer)
        assert owner.post(borrow_path + "/conversation", headers=headers).status_code == 403
    assert buyer.post(f"/api/items/{item['id']}/conversations", headers=ORIGIN, json={"participant_b_id": other.get('/api/auth/me').json()['id']}).status_code == 422
    assert send(buyer, chat["id"], "伪造", sender_id=owner.get('/api/auth/me').json()['id']).status_code == 422
    for route in (path, path + "/messages"):
        assert other.get(route).status_code == 404
    assert send(other, chat["id"], "越权消息").status_code == 404
    assert other.get("/api/conversations").json()["conversations"] == []
    for private_key in ("student_no", "password_hash", "token_hash", "CHAT_OWNER", "CHAT_BUYER"):
        assert private_key not in str(buyer.get("/api/conversations").json())


@pytest.mark.parametrize("content", ["", " \t\n ", "字" * 1001, None, 123])
def test_invalid_content_rejected(actors, content):
    _, buyer, _, item = actors
    chat = sale_chat(buyer, item).json()
    assert send(buyer, chat["id"], content).status_code == 422
    assert buyer.get(f"/api/conversations/{chat['id']}/messages").json()["messages"] == []


def test_persistence_plain_text_and_stable_cursor_pagination(actors, test_app):
    owner, buyer, _, item = actors
    chat = sale_chat(buyer, item).json(); path = f"/api/conversations/{chat['id']}/messages"
    values = ["  第一条  ", "<script>alert('text')</script>", "第三条", "第四条", "字" * 1000]
    messages = [send(buyer if i % 2 == 0 else owner, chat["id"], value).json() for i, value in enumerate(values)]
    assert messages[0]["content"] == "第一条"
    assert messages[1]["content"] == values[1]
    assert messages[0]["sender_id"] == buyer.get('/api/auth/me').json()['id']
    assert all(message["created_at"].endswith("Z") for message in messages)
    with test_app.state.session_factory() as db:
        assert len(db.scalars(select(Message).where(Message.conversation_id == chat["id"])).all()) == 5
    with TestClient(test_app) as reopened:
        reopened.cookies.update(buyer.cookies)
        latest = reopened.get(path + "?limit=2").json()
        assert [row["id"] for row in latest["messages"]] == [row["id"] for row in messages[-2:]] and latest["has_more"]
        older = reopened.get(path + f"?limit=2&before_id={messages[3]['id']}").json()
        assert older["messages"] == messages[1:3] and older["has_more"]
        oldest = reopened.get(path + f"?limit=2&before_id={messages[1]['id']}").json()
        assert oldest["messages"] == messages[:1] and not oldest["has_more"]
        new = reopened.get(path + f"?limit=2&after_id={messages[1]['id']}").json()
        assert new["messages"] == messages[2:4] and new["has_more"]
        assert reopened.get(path + "?before_id=1&after_id=0").status_code == 422
        assert reopened.get(path + "?limit=51").status_code == 422
        assert reopened.get("/api/conversations?page_size=1").json()["conversations"][0]["last_message"]["content"] == "字" * 100


@pytest.mark.parametrize("context", ["sale_item", "borrow_request"])
def test_concurrent_create_reuses_one_conversation_and_unique_constraint(actors, test_app, context):
    owner, buyer, _, item = actors
    if context == "sale_item":
        path = f"/api/items/{item['id']}/conversations"
    else:
        _, _, borrow_path = borrow_fixture(owner, buyer)
        owner.post(borrow_path + "/approve", headers=ORIGIN)
        path = borrow_path + "/conversation"
    barrier = Barrier(2)

    def create_at_once(_):
        with TestClient(test_app) as worker:
            worker.cookies.update(buyer.cookies)
            barrier.wait(timeout=5)
            response = worker.post(path, headers=ORIGIN)
            assert response.status_code == 200
            return response.json()["id"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(create_at_once, range(2)))
    assert ids[0] == ids[1]
    with test_app.state.session_factory() as db:
        rows = db.scalars(select(Conversation).where(Conversation.context_type == context)).all()
        assert len(rows) == 1
        row = rows[0]
        db.add(Conversation(context_type=context, item_id=row.item_id, borrow_request_id=row.borrow_request_id,
                            participant_a_id=row.participant_a_id, participant_b_id=row.participant_b_id))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
