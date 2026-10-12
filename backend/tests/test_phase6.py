from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.gift_request import GiftRequest
from app.models.user import User
from test_borrows import PAYLOAD
from test_items import ORIGIN, item_payload, register_and_login


@pytest.fixture
def actors(client, test_app):
    register_and_login(client, "P6_OWNER", "物主同学")
    with TestClient(test_app) as buyer, TestClient(test_app) as other:
        register_and_login(buyer, "P6_BUYER", "申请同学")
        register_and_login(other, "P6_OTHER", "其他同学")
        yield client, buyer, other


def item(owner, mode="sale", **changes):
    payload = item_payload() | {"mode": mode, **changes}
    if mode != "sale":
        payload["price_cents"] = None
    if mode != "borrow":
        payload["borrow_note"] = None
    response = owner.post("/api/items", headers=ORIGIN, json=payload)
    assert response.status_code == 201
    return response.json()


def grant(test_app, actor):
    user_id = actor.get("/api/auth/me").json()["id"]
    with test_app.state.session_factory() as db:
        db.get(User, user_id).is_admin = True
        db.commit()


def report(actor, kind, target_id):
    return actor.post("/api/reports", headers=ORIGIN, json={"target_type": kind, "target_id": target_id, "reason": "描述不符", "description": "请人工复核该记录"})


def gift(actor, published):
    return actor.post(f"/api/items/{published['id']}/gift-requests", headers=ORIGIN, json={"note": "周末交接"})


def act(actor, gift_id, action):
    return actor.post(f"/api/gifts/{gift_id}/{action}", headers=ORIGIN)


def test_report_resolution_single_appeal_and_private_scope(actors, test_app):
    owner, buyer, other = actors
    published = item(owner)
    trade = buyer.post(f"/api/items/{published['id']}/trade-intents", headers=ORIGIN, json={}).json()
    created = report(buyer, "trade", trade["id"])
    assert created.status_code == 201
    row = created.json(); path = f"/api/reports/{row['id']}"; admin_path = f"/api/admin/reports/{row['id']}"
    assert buyer.get("/api/admin/reports").status_code == 403
    assert buyer.get(admin_path).status_code == 403
    assert buyer.get("/api/reports/mine").json()["total"] == 1
    assert other.get("/api/reports/mine").json()["total"] == 0
    assert other.get(path).status_code == 404
    assert other.post(path + "/appeal", headers=ORIGIN, json={"reason": "越权"}).status_code == 404
    assert buyer.post(path + "/appeal", headers=ORIGIN, json={"reason": "未处理"}).status_code == 409
    grant(test_app, owner)
    assert owner.get("/api/auth/me").json()["is_admin"] is True
    assert owner.post(admin_path + "/resolve", json={"status": "handled", "note": "说明"}).status_code == 403
    resolved = owner.post(admin_path + "/resolve", headers=ORIGIN, json={"status": "dismissed", "note": "初步证据不足"})
    assert resolved.status_code == 200 and resolved.json()["resolved_at"].endswith("Z")
    assert buyer.get(path).json()["resolution_note"] == "初步证据不足"
    assert buyer.post(path + "/appeal", headers=ORIGIN, json={"reason": "补充具体情况"}).json()["appeal"]["status"] == "pending"
    assert buyer.post(path + "/appeal", headers=ORIGIN, json={"reason": "重复"}).status_code == 409
    assert owner.get("/api/admin/reports?appeal_pending=true").json()["total"] == 1
    reviewed = owner.post(admin_path + "/appeal-review", headers=ORIGIN, json={"status": "handled", "note": "已核对补充情况并反馈"}).json()
    assert reviewed["appeal"]["status"] == "reviewed" and reviewed["appeal"]["decision"] == "handled"
    assert reviewed["status"] == "dismissed"  # Original conclusion is preserved.
    assert buyer.get(path).json()["appeal"]["review_note"] == "已核对补充情况并反馈"
    assert owner.post(admin_path + "/appeal-review", headers=ORIGIN, json={"status": "handled", "note": "重复"}).status_code == 409
    assert buyer.get("/api/trades/mine").json()["trades"][0]["status"] == "pending"
    assert not any(key in str(buyer.get(path).json()) for key in ("student_no", "password_hash", "token_hash", "P6_OWNER"))


def test_private_report_targets_and_admin_message_evidence_are_bounded(actors, test_app):
    owner, buyer, other = actors
    sale = item(owner)
    trade = buyer.post(f"/api/items/{sale['id']}/trade-intents", headers=ORIGIN, json={}).json()
    borrowed = item(owner, "borrow")
    borrow = buyer.post(f"/api/items/{borrowed['id']}/borrow-requests", headers=ORIGIN, json=PAYLOAD).json()
    conversation = buyer.post(f"/api/items/{sale['id']}/conversations", headers=ORIGIN).json()
    path = f"/api/conversations/{conversation['id']}/messages"
    message = owner.post(path, headers=ORIGIN, json={"content": "需要审阅的选中消息"}).json()
    owner.post(path, headers=ORIGIN, json={"content": "未提交的另一条私人消息"})
    grant(test_app, other)
    for kind, target_id in (("trade", trade["id"]), ("borrow", borrow["id"]), ("message", message["id"])):
        assert report(other, kind, target_id).status_code == 404
        assert report(buyer, kind, target_id).status_code == 201
    message_report = report(buyer, "message", message["id"]).json()
    detail = other.get(f"/api/admin/reports/{message_report['id']}").json()
    assert detail["evidence"]["content"] == message["content"]
    assert "未提交的另一条私人消息" not in str(detail)
    assert "evidence" not in other.get("/api/admin/reports").json()["reports"][0]
    assert other.get(path).status_code == 404  # Admin role grants no general chat access.
    assert buyer.get("/api/borrows/mine").json()["borrows"][0]["status"] == "pending"


def test_public_report_snapshot_survives_edit_and_origin_auth_role_spoofing(actors, test_app):
    owner, buyer, _ = actors
    published = item(owner)
    row = report(buyer, "item", published["id"]).json()
    owner.patch(f"/api/items/{published['id']}", headers=ORIGIN, json={"title": "后来修改"})
    owner.delete(f"/api/items/{published['id']}", headers=ORIGIN)
    assert report(buyer, "item", published["id"]).status_code == 404
    assert buyer.get(f"/api/reports/{row['id']}").json()["evidence"]["title"] == published["title"]
    assert report(owner, "item", published["id"]).status_code == 201
    with TestClient(test_app) as anonymous:
        assert report(anonymous, "item", published["id"]).status_code == 401
        assert anonymous.get("/api/admin/reports").status_code == 401
        assert anonymous.post("/api/auth/register", headers=ORIGIN, json={"student_no": "ROLE_SPOOF", "nickname": "伪造角色", "campus": "五山校区", "password": "Test-only-password", "is_admin": True}).status_code == 422
    assert buyer.post("/api/reports", json={"target_type": "item", "target_id": 1, "reason": "原因", "description": "内容"}).status_code == 403
    assert buyer.post("/api/reports", headers=ORIGIN, json={"target_type": "item", "target_id": 1, "reason": " ", "description": "内容", "reporter_id": 999}).status_code == 422
    assert buyer.get("/api/auth/me").json()["is_admin"] is False


def test_gift_full_flow_duplicate_and_unrelated_operations(actors):
    owner, buyer, other = actors
    published = item(owner, "gift")
    first, second = gift(buyer, published).json(), gift(other, published).json()
    assert gift(buyer, published).status_code == 409
    assert gift(owner, published).status_code == 409
    assert act(other, first["id"], "confirm").status_code == 404
    assert act(buyer, first["id"], "approve").status_code == 403
    assert act(buyer, first["id"], "confirm").status_code == 409
    approved = act(owner, first["id"], "approve").json()
    assert approved["status"] == "approved"
    assert other.get("/api/gifts/mine").json()["gifts"][0]["status"] == "rejected"
    assert act(owner, second["id"], "approve").status_code == 409
    single = act(buyer, first["id"], "confirm").json()
    assert single["status"] == "approved" and single["completed_at"] is None
    assert act(owner, first["id"], "cancel").status_code == 409
    completed = act(owner, first["id"], "confirm").json()
    assert completed["status"] == "completed" and completed["completed_at"].endswith("Z")
    assert act(buyer, first["id"], "confirm").json() == completed
    assert owner.get(f"/api/items/{published['id']}").json()["availability"] == "gifted"
    assert gift(other, published).status_code == 409
    assert act(owner, first["id"], "cancel").status_code == 409
    assert buyer.get("/api/trades/mine").json()["total"] == 0


@pytest.mark.parametrize("role", ["owner", "recipient"])
def test_gift_cancel_restores_available_and_pending_reject(actors, role):
    owner, buyer, other = actors
    published = item(owner, "gift")
    pending = gift(buyer, published).json()
    assert act(owner, pending["id"], "reject").json()["status"] == "rejected"
    pending = gift(buyer, published).json()
    assert act(buyer, pending["id"], "cancel").json()["status"] == "canceled"
    pending = gift(buyer, published).json()
    act(owner, pending["id"], "approve")
    assert act(owner if role == "owner" else buyer, pending["id"], "cancel").json()["status"] == "canceled"
    assert buyer.get(f"/api/items/{published['id']}").json()["availability"] == "available"
    assert gift(other, published).status_code == 201


def test_gift_price_mode_and_dangerous_edits_origin(actors, test_app):
    owner, buyer, _ = actors
    for value in (0, 100, -1):
        assert owner.post("/api/items", headers=ORIGIN, json=item_payload() | {"mode": "gift", "price_cents": value}).status_code == 422
    assert owner.post("/api/items", headers=ORIGIN, json=item_payload("borrow") | {"mode": "gift", "price_cents": None}).status_code == 422
    sale = item(owner)
    assert gift(buyer, sale).status_code == 409
    changed = owner.patch(f"/api/items/{sale['id']}", headers=ORIGIN, json={"mode": "gift"}).json()
    assert changed["price_cents"] is None and changed["borrow_note"] is None
    created = gift(buyer, changed).json()
    for state in ("pending", "approved", "completed"):
        assert owner.patch(f"/api/items/{sale['id']}", headers=ORIGIN, json={"mode": "sale", "price_cents": 1200}).status_code == 409
        assert owner.delete(f"/api/items/{sale['id']}", headers=ORIGIN).status_code == 409
        assert owner.patch(f"/api/items/{sale['id']}", headers=ORIGIN, json={"description": "仍可补充说明"}).status_code == 200
        if state == "pending":
            act(owner, created["id"], "approve")
        elif state == "approved":
            act(owner, created["id"], "confirm"); act(buyer, created["id"], "confirm")
    for action in ("approve", "reject", "cancel", "confirm"):
        assert buyer.post(f"/api/gifts/{created['id']}/{action}").status_code == 403
    with TestClient(test_app) as anonymous:
        assert gift(anonymous, sale).status_code == 401
        assert anonymous.get("/api/gifts/mine").status_code == 401
    withdrawn = item(owner, "gift")
    owner.delete(f"/api/items/{withdrawn['id']}", headers=ORIGIN)
    assert gift(buyer, withdrawn).status_code == 409


def test_concurrent_gift_approvals_and_database_uniqueness(actors, test_app):
    owner, buyer, other = actors
    published = item(owner, "gift")
    first, second = gift(buyer, published).json(), gift(other, published).json()
    barrier = Barrier(2)
    def at_once(gift_id):
        with TestClient(test_app) as worker:
            worker.cookies.update(owner.cookies); barrier.wait(timeout=5)
            return act(worker, gift_id, "approve").status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(at_once, (first["id"], second["id"])))
    assert sorted(results) == [200, 409]
    with test_app.state.session_factory() as db:
        rows = db.scalars(select(GiftRequest).where(GiftRequest.item_id == published["id"])).all()
        assert sorted(row.status for row in rows) == ["approved", "rejected"]
        loser = next(row for row in rows if row.status == "rejected")
        db.add(GiftRequest(item_id=published["id"], owner_id=loser.owner_id, recipient_id=loser.recipient_id, status="approved"))
        with pytest.raises(IntegrityError): db.commit()
        db.rollback()


def test_price_reference_public_filters_and_insufficient_same_campus(actors):
    owner, buyer, _ = actors
    current = item(owner, title="Canon摄影相机")
    valid = [item(owner, title=f"Canon相机{suffix}", price_cents=price, campus=campus) for suffix, price, campus in (("甲", 1000, "五山校区"), ("乙", 2300, "五山校区"), ("丙", 3400, "大学城校区"))]
    excluded = [item(owner, title="Canon相机下架"), item(owner, title="Canon相机预留"), item(owner, title="Canon相机售出")]
    owner.delete(f"/api/items/{excluded[0]['id']}", headers=ORIGIN)
    for i, row in enumerate(excluded[1:]):
        trade = buyer.post(f"/api/items/{row['id']}/trade-intents", headers=ORIGIN, json={}).json()
        path = f"/api/trades/{trade['id']}"
        owner.post(path + "/accept", headers=ORIGIN)
        if i == 1:
            owner.post(path + "/confirm", headers=ORIGIN); buyer.post(path + "/confirm", headers=ORIGIN)
    item(owner, title="Canon相机其他类别", category="其他")
    item(owner, title="无关书桌")
    gift_item = item(owner, "gift", title="Canon相机转赠")
    item(owner, "borrow", title="Canon相机借还")
    path = f"/api/items/{current['id']}/price-reference"
    result = buyer.get(path).json()
    assert {row["id"] for row in result["items"]} == {row["id"] for row in valid}
    assert result["sample_count"] == 3 and result["min_price_cents"] == 1000 and result["max_price_cents"] == 3400
    assert result["disclaimer"] == "仅供参考，展示的是当前挂牌价，不代表实际成交价或公允价格。"
    limited = buyer.get(path + "?same_campus=true").json()
    assert limited["sample_count"] == 2 and limited["min_price_cents"] is None
    assert buyer.get(f"/api/items/{gift_item['id']}/price-reference").status_code == 409
    assert not any(key in str(result) for key in ("student_no", "password_hash", "owner"))
