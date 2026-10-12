import io
from pathlib import Path

from PIL import Image
import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.item import ItemImage

ORIGIN = {"Origin": "http://127.0.0.1:5173"}
PASSWORD = "Test-only-password-123"


def register_and_login(client, student_no, nickname):
    response = client.post("/api/auth/register", headers=ORIGIN, json={
        "student_no": student_no, "nickname": nickname, "password": PASSWORD, "campus": "五山校区",
    })
    assert response.status_code == 201
    assert client.post("/api/auth/login", headers=ORIGIN, json={"student_no": student_no, "password": PASSWORD}).status_code == 200


def item_payload(mode="sale"):
    return {
        "title": "测试相机",
        "description": "用于物品 API 测试",
        "category": "数码配件",
        "mode": mode,
        "campus": "五山校区",
        "price_cents": 1200 if mode == "sale" else None,
        "borrow_note": None if mode == "sale" else "请爱惜使用并按时归还",
        "interest_tags": ["摄影", "数码"],
    }


def png_file():
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), "green").save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def image_file(image_format):
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), "green").save(buffer, format=image_format)
    buffer.seek(0)
    return buffer


def test_item_lifecycle_and_public_redaction(client):
    register_and_login(client, "ITEM_OWNER", "物主")
    created = client.post("/api/items", headers=ORIGIN, json=item_payload())
    assert created.status_code == 201
    item_id = created.json()["id"]
    assert created.json()["interest_tags"] == ["摄影", "数码"]
    assert client.get("/api/items?q=相机&category=数码配件&campus=五山校区").json()["total"] == 1
    public_list = client.get("/api/items").json()
    public_detail = client.get(f"/api/items/{item_id}").json()
    for public_item in [*public_list["items"], public_detail]:
        assert public_item["owner"] == {"id": created.json()["owner_id"], "nickname": "物主"}
        assert not {"student_no", "student_no_masked", "password_hash", "token_hash", "auth_sessions"}.intersection(public_item)
        assert "ITEM_OWNER" not in str(public_item)
    assert client.patch(f"/api/items/{item_id}", headers=ORIGIN, json={"title": "已编辑相机"}).status_code == 200
    assert client.delete(f"/api/items/{item_id}", headers=ORIGIN).status_code == 200
    assert client.get(f"/api/items/{item_id}").status_code == 404
    assert client.get("/api/items").json()["total"] == 0
    assert client.delete(f"/api/items/{item_id}", headers=ORIGIN).status_code == 200
    mine = client.get("/api/items/mine")
    assert mine.status_code == 200 and mine.json()["items"][0]["status"] == "withdrawn"


def test_borrow_is_free_and_validation(client):
    register_and_login(client, "BORROW_OWNER", "借用物主")
    response = client.post("/api/items", headers=ORIGIN, json=item_payload("borrow"))
    assert response.status_code == 201 and response.json()["price_cents"] is None
    invalid = item_payload("borrow") | {"price_cents": 100}
    assert client.post("/api/items", headers=ORIGIN, json=invalid).status_code == 422
    invalid_sale = item_payload("sale") | {"price_cents": 0}
    assert client.post("/api/items", headers=ORIGIN, json=invalid_sale).status_code == 422
    for invalid_price in (-1, None, 1.5, True, "1200", "not-a-price", 100_000_001):
        payload = item_payload("sale") | {"price_cents": invalid_price}
        assert client.post("/api/items", headers=ORIGIN, json=payload).status_code == 422


def test_anonymous_and_cross_user_permissions(client, test_app):
    assert client.post("/api/items", headers=ORIGIN, json=item_payload()).status_code == 401
    register_and_login(client, "OWNER_A", "甲同学")
    item_id = client.post("/api/items", headers=ORIGIN, json=item_payload()).json()["id"]
    owner_item = client.post(f"/api/items/{item_id}/images", headers=ORIGIN, files={"file": ("owner.png", png_file(), "image/png")}).json()
    image_id = owner_item["images"][0]["id"]
    from fastapi.testclient import TestClient
    with TestClient(test_app) as anonymous:
        assert anonymous.get("/api/items").json()["total"] == 1
        assert anonymous.get(f"/api/items/{item_id}").status_code == 200
        assert anonymous.get("/api/items/mine").status_code == 401
        assert anonymous.patch(f"/api/items/{item_id}", headers=ORIGIN, json={"title": "匿名修改"}).status_code == 401
        assert anonymous.delete(f"/api/items/{item_id}", headers=ORIGIN).status_code == 401
    from fastapi.testclient import TestClient
    with TestClient(test_app) as other:
        register_and_login(other, "OWNER_B", "乙同学")
        assert other.patch(f"/api/items/{item_id}", headers=ORIGIN, json={"title": "越权"}).status_code == 404
        assert other.delete(f"/api/items/{item_id}", headers=ORIGIN).status_code == 404
        assert other.post(f"/api/items/{item_id}/images", headers=ORIGIN, files={"file": ("a.png", png_file(), "image/png")}).status_code == 404
        assert other.delete(f"/api/items/{item_id}/images/{image_id}", headers=ORIGIN).status_code == 404


def test_search_filters_pagination_and_mine_are_scoped(client, test_app):
    register_and_login(client, "LIST_OWNER_A", "甲同学")
    first = client.post("/api/items", headers=ORIGIN, json=item_payload() | {"title": "相机甲", "category": "数码配件"}).json()
    second = client.post("/api/items", headers=ORIGIN, json=item_payload("borrow") | {"title": "教材乙", "category": "教材资料", "campus": "大学城校区"}).json()
    from fastapi.testclient import TestClient
    with TestClient(test_app) as other:
        register_and_login(other, "LIST_OWNER_B", "乙同学")
        third = other.post("/api/items", headers=ORIGIN, json=item_payload() | {"title": "相机丙"}).json()
        assert other.get("/api/items?q=相机").json()["total"] == 2
        assert other.get("/api/items?category=教材资料&campus=大学城校区&mode=borrow").json()["items"][0]["id"] == second["id"]
        page = other.get("/api/items?page=1&page_size=1")
        assert page.json()["total"] == 3 and len(page.json()["items"]) == 1
        assert other.get("/api/items?page=2&page_size=1").json()["items"][0]["id"] != page.json()["items"][0]["id"]
        assert [item["id"] for item in other.get("/api/items/mine").json()["items"]] == [third["id"]]
    assert [item["id"] for item in client.get("/api/items/mine").json()["items"]] == [second["id"], first["id"]]


@pytest.mark.parametrize("headers", [{}, {"Origin": "https://example.com"}])
def test_item_write_routes_keep_origin_validation(client, headers):
    assert client.post("/api/items", json=item_payload()).status_code == 403
    assert client.post("/api/items", headers={"Origin": "https://example.com"}, json=item_payload()).status_code == 403
    assert client.post("/api/items", headers=ORIGIN, json=item_payload()).status_code == 401
    register_and_login(client, "ORIGIN_OWNER", "来源测试")
    item_id = client.post("/api/items", headers=ORIGIN, json=item_payload()).json()["id"]
    uploaded = client.post(f"/api/items/{item_id}/images", headers=ORIGIN, files={"file": ("a.png", png_file(), "image/png")}).json()
    image_id = uploaded["images"][0]["id"]
    assert client.post("/api/items", headers=headers, json=item_payload()).status_code == 403
    assert client.patch(f"/api/items/{item_id}", headers=headers, json={"title": "不能修改"}).status_code == 403
    assert client.delete(f"/api/items/{item_id}", headers=headers).status_code == 403
    assert client.post(f"/api/items/{item_id}/images", headers=headers, files={"file": ("a.png", png_file(), "image/png")}).status_code == 403
    assert client.delete(f"/api/items/{item_id}/images/{image_id}", headers=headers).status_code == 403
    assert client.get("/api/auth/me").status_code == 200
    assert client.get(f"/api/items/{item_id}").json()["title"] == "测试相机"


@pytest.mark.parametrize("method,field", [("post", "owner_id"), ("post", "status"), ("patch", "owner_id"), ("patch", "status")])
def test_client_cannot_assign_owner_or_internal_status(client, method, field):
    register_and_login(client, "SERVER_OWNER", "会话物主")
    created = client.post("/api/items", headers=ORIGIN, json=item_payload()).json()
    assert created["owner_id"] == client.get("/api/auth/me").json()["id"]
    value = 999 if field == "owner_id" else "withdrawn"
    path = "/api/items" if method == "post" else f"/api/items/{created['id']}"
    payload = item_payload() | {field: value} if method == "post" else {field: value}
    assert client.request(method, path, headers=ORIGIN, json=payload).status_code == 422
    assert client.get(f"/api/items/{created['id']}").json()["owner_id"] == created["owner_id"]


@pytest.mark.parametrize("changes", [
    {"title": "   "}, {"title": None}, {"description": None}, {"interest_tags": None},
    {"price_cents": None}, {"mode": "borrow", "price_cents": 100}, {"borrow_note": "不适用"},
])
def test_patch_revalidates_full_item_and_keeps_data_on_failure(client, changes):
    register_and_login(client, "PATCH_OWNER", "编辑校验")
    created = client.post("/api/items", headers=ORIGIN, json=item_payload()).json()
    response = client.patch(f"/api/items/{created['id']}", headers=ORIGIN, json=changes)
    assert response.status_code == 422
    assert client.get(f"/api/items/{created['id']}").json() == created


def test_mode_switch_clears_inapplicable_fields_and_updates_tags(client):
    register_and_login(client, "SWITCH_OWNER", "切换测试")
    item_id = client.post("/api/items", headers=ORIGIN, json=item_payload()).json()["id"]
    borrowed = client.patch(f"/api/items/{item_id}", headers=ORIGIN, json={"mode": "borrow", "borrow_note": "免费借用", "interest_tags": ["学习"]})
    assert borrowed.status_code == 200 and borrowed.json()["price_cents"] is None
    assert borrowed.json()["interest_tags"] == ["学习"]
    assert client.patch(f"/api/items/{item_id}", headers=ORIGIN, json={"mode": "sale"}).status_code == 422
    sold = client.patch(f"/api/items/{item_id}", headers=ORIGIN, json={"mode": "sale", "price_cents": 200})
    assert sold.status_code == 200 and sold.json()["borrow_note"] is None


def test_jpeg_png_webp_upload_and_limit(client):
    register_and_login(client, "IMAGE_OWNER", "图片物主")
    item_id = client.post("/api/items", headers=ORIGIN, json=item_payload()).json()["id"]
    for image_format, media_type in (("JPEG", "image/jpeg"), ("PNG", "image/png"), ("WEBP", "image/webp")):
        response = client.post(f"/api/items/{item_id}/images", headers=ORIGIN, files={"file": ("image.svg", image_file(image_format), "image/svg+xml")})
        assert response.status_code == 200
        assert response.json()["images"][-1]["content_type"] == media_type
    too_many = client.post(f"/api/items/{item_id}/images", headers=ORIGIN, files={"file": ("a.png", png_file(), "image/png")})
    assert too_many.status_code == 409
    item = client.get(f"/api/items/{item_id}").json()
    assert len(item["images"]) == 3 and client.get(item["images"][0]["url"]).status_code == 200


def test_invalid_image_bytes_and_oversize_are_rejected(client, test_app):
    register_and_login(client, "BAD_IMAGE_OWNER", "图片测试")
    item_id = client.post("/api/items", headers=ORIGIN, json=item_payload()).json()["id"]
    fake_svg = client.post(f"/api/items/{item_id}/images", headers=ORIGIN, files={"file": ("fake.png", b"<svg><script>alert(1)</script></svg>", "image/png")})
    assert fake_svg.status_code == 415
    oversized = client.post(f"/api/items/{item_id}/images", headers=ORIGIN, files={"file": ("large.png", b"x" * (5 * 1024 * 1024 + 1), "image/png")})
    assert oversized.status_code == 413
    assert client.get(f"/api/items/{item_id}").json()["images"] == []
    assert list(test_app.state.settings.resolved_upload_dir.glob("*")) == []


def test_image_delete_keeps_database_and_files_consistent(client, test_app):
    register_and_login(client, "DELETE_IMAGE_OWNER", "删除图片测试")
    item_id = client.post("/api/items", headers=ORIGIN, json=item_payload()).json()["id"]
    uploaded = client.post(f"/api/items/{item_id}/images", headers=ORIGIN, files={"file": ("a.png", png_file(), "image/png")}).json()
    image_id = uploaded["images"][0]["id"]
    file_name = uploaded["images"][0]["url"].rsplit("/", 1)[-1]
    path = test_app.state.settings.resolved_upload_dir / file_name
    assert path.exists()
    deleted = client.delete(f"/api/items/{item_id}/images/{image_id}", headers=ORIGIN)
    assert deleted.status_code == 200 and deleted.json()["images"] == []
    assert not path.exists()
    with test_app.state.session_factory() as db:
        assert db.scalar(select(ItemImage).where(ItemImage.id == image_id)) is None


def test_image_upload_commit_failure_removes_file_and_record(client, test_app, monkeypatch):
    register_and_login(client, "FAILED_IMAGE_OWNER", "上传失败测试")
    item_id = client.post("/api/items", headers=ORIGIN, json=item_payload()).json()["id"]
    original_commit = Session.commit

    def fail_when_image_is_added(session):
        if any(isinstance(value, ItemImage) for value in session.new):
            raise SQLAlchemyError("test-only commit failure")
        original_commit(session)

    monkeypatch.setattr(Session, "commit", fail_when_image_is_added)
    response = client.post(f"/api/items/{item_id}/images", headers=ORIGIN, files={"file": ("a.png", png_file(), "image/png")})
    assert response.status_code == 503
    assert list(test_app.state.settings.resolved_upload_dir.glob("*")) == []
    monkeypatch.setattr(Session, "commit", original_commit)
    with test_app.state.session_factory() as db:
        assert db.scalars(select(ItemImage)).all() == []


def test_image_delete_commit_failure_restores_file_and_record(client, test_app, monkeypatch):
    register_and_login(client, "FAILED_DELETE_OWNER", "删除失败测试")
    item_id = client.post("/api/items", headers=ORIGIN, json=item_payload()).json()["id"]
    uploaded = client.post(f"/api/items/{item_id}/images", headers=ORIGIN, files={"file": ("a.png", png_file(), "image/png")}).json()
    image_id = uploaded["images"][0]["id"]
    file_name = uploaded["images"][0]["url"].rsplit("/", 1)[-1]
    path = test_app.state.settings.resolved_upload_dir / file_name
    original_commit = Session.commit

    def fail_when_image_is_deleted(session):
        if any(isinstance(value, ItemImage) for value in session.deleted):
            raise SQLAlchemyError("test-only delete failure")
        original_commit(session)

    monkeypatch.setattr(Session, "commit", fail_when_image_is_deleted)
    response = client.delete(f"/api/items/{item_id}/images/{image_id}", headers=ORIGIN)
    assert response.status_code == 503
    assert path.exists()
    monkeypatch.setattr(Session, "commit", original_commit)
    with test_app.state.session_factory() as db:
        assert db.scalar(select(ItemImage).where(ItemImage.id == image_id)) is not None


def test_image_file_delete_failure_keeps_record_and_file(client, test_app, monkeypatch):
    register_and_login(client, "FILE_DELETE_OWNER", "文件删除失败")
    item_id = client.post("/api/items", headers=ORIGIN, json=item_payload()).json()["id"]
    uploaded = client.post(f"/api/items/{item_id}/images", headers=ORIGIN, files={"file": ("a.png", png_file(), "image/png")}).json()
    image = uploaded["images"][0]
    path = test_app.state.settings.resolved_upload_dir / image["url"].rsplit("/", 1)[-1]
    original_unlink = Path.unlink

    def fail_only_image(candidate, *args, **kwargs):
        if candidate == path:
            raise OSError("test-only file lock")
        return original_unlink(candidate, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_only_image)
    assert client.delete(f"/api/items/{item_id}/images/{image['id']}", headers=ORIGIN).status_code == 503
    assert path.is_file()
    assert client.get(f"/api/items/{item_id}").json()["images"] == [image]


@pytest.mark.parametrize("route", ["/api/items", "/api/items/mine"])
def test_invalid_item_query_parameters_are_rejected(client, route):
    if route.endswith("/mine"):
        register_and_login(client, "INVALID_QUERY_OWNER", "参数测试")
    assert client.get(f"{route}?page=0").status_code == 422
    assert client.get(f"{route}?page_size=51").status_code == 422
    if route == "/api/items":
        for query in ("mode=unknown", "category=不存在", "campus=不存在", "min_price_cents=-1", "min_price_cents=200&max_price_cents=100", "q=" + "x" * 101):
            assert client.get(f"{route}?{query}").status_code == 422
