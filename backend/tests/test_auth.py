from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.core.security import password_hasher, token_hash
from app.models.auth_session import AuthSession
from app.models.user import User

ORIGIN = {"Origin": "http://127.0.0.1:5173"}
PASSWORD = "Test-only-password-123"


def register(client, student_no="TEST_2026_001", nickname="测试同学"):
    return client.post("/api/auth/register", headers=ORIGIN, json={
        "student_no": student_no, "nickname": nickname, "password": PASSWORD, "campus": "五山校区",
    })


def login(client, student_no="TEST_2026_001", password=PASSWORD):
    return client.post("/api/auth/login", headers=ORIGIN, json={"student_no": student_no, "password": password})


def test_register_public_response_and_trimmed_fields(client, test_app):
    response = register(client, student_no="  TEST_2026_001  ", nickname="  测试同学  ")
    assert response.status_code == 201
    assert set(response.json()) == {"id", "nickname", "campus", "created_at"}
    assert response.json()["nickname"] == "测试同学"
    assert response.json()["created_at"].endswith("Z")
    assert PASSWORD not in response.text
    with test_app.state.session_factory() as db:
        user = db.scalar(select(User))
        assert user.student_no == "TEST_2026_001"
        assert user.password_hash.startswith("$argon2id$")
        assert PASSWORD != user.password_hash
        assert password_hasher.verify(user.password_hash, PASSWORD)
    assert client.get("/api/auth/me").status_code == 401  # Registration does not log in.


def test_duplicate_nickname_is_allowed(client):
    assert register(client, "ACCOUNT_A").status_code == 201
    assert register(client, "ACCOUNT_B").status_code == 201


def test_duplicate_student_no_is_rejected(client):
    assert register(client).status_code == 201
    response = register(client, nickname="另一昵称")
    assert response.status_code == 409
    assert "password" not in response.text


@pytest.mark.parametrize("field", ["nickname", "student_no", "password", "campus"])
def test_missing_required_field(client, field):
    payload = {"nickname": "测试同学", "student_no": "ACCOUNT_A", "password": PASSWORD, "campus": "五山校区"}
    del payload[field]
    response = client.post("/api/auth/register", headers=ORIGIN, json=payload)
    assert response.status_code == 422
    assert PASSWORD not in response.text
    assert all("input" not in error for error in response.json()["detail"])


@pytest.mark.parametrize(("field", "value"), [
    ("nickname", " "), ("nickname", "a"), ("nickname", "同" * 31),
    ("student_no", "a"), ("student_no", "abc@123"), ("student_no", "a" * 33),
    ("campus", "其他校区"), ("password", "p@5"), ("password", "x" * 129),
])
def test_invalid_registration_is_rejected_without_echoing_input(client, field, value):
    payload = {"nickname": "测试同学", "student_no": "ACCOUNT_A", "password": PASSWORD, "campus": "五山校区"}
    payload[field] = value
    response = client.post("/api/auth/register", headers=ORIGIN, json=payload)
    assert response.status_code == 422
    assert PASSWORD not in response.text
    if field == "password":
        assert value not in response.text


@pytest.mark.parametrize("campus", ["五山校区", "大学城校区", "广州国际校区"])
def test_all_three_campuses_are_accepted(client, campus):
    response = client.post("/api/auth/register", headers=ORIGIN, json={
        "nickname": "测试同学", "student_no": "A-1", "password": PASSWORD, "campus": campus,
    })
    assert response.status_code == 201
    assert response.json()["campus"] == campus


def test_database_itself_enforces_unique_student_no_and_campus(client, test_app):
    register(client)
    with test_app.state.session_factory() as db:
        with pytest.raises(IntegrityError):
            db.execute(User.__table__.insert().values(
                nickname="不同昵称", student_no="TEST_2026_001", password_hash="test_hash", campus="五山校区",
            ))
            db.commit()
        db.rollback()
        with pytest.raises(IntegrityError):
            db.execute(User.__table__.insert().values(
                nickname="非法校区", student_no="OTHER_ACCOUNT", password_hash="test_hash", campus="不存在的校区",
            ))
            db.commit()
        db.rollback()


def test_login_cookie_and_hash_only_session_storage(client, test_app):
    register(client)
    response = login(client)
    assert response.status_code == 200
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie and "path=/api" in cookie
    assert "max-age=3600" in cookie and "expires=" in cookie
    token = client.cookies.get("scut_share_session")
    assert len(token) >= 43
    with test_app.state.session_factory() as db:
        session = db.scalar(select(AuthSession))
        assert session.token_hash == token_hash(token)
        assert session.token_hash != token
    assert token not in response.text
    assert response.headers["cache-control"] == "no-store"


def test_wrong_password_and_unknown_account_have_identical_responses(client):
    register(client)
    wrong = login(client, password="Wrong-password")
    unknown = login(client, student_no="UNKNOWN_ACCOUNT", password="Wrong-password")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {"detail": "学号或密码错误。"}
    assert "set-cookie" not in wrong.headers and "set-cookie" not in unknown.headers


def test_anonymous_me_is_unauthorized(client):
    assert client.get("/api/auth/me").status_code == 401


def test_private_info_contains_only_masked_student_no(client, test_app):
    register(client)
    login(client)
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert set(response.json()) == {"id", "nickname", "campus", "created_at", "student_no_masked", "is_admin"}
    assert response.json()["student_no_masked"] == "*********_001"
    assert "TEST_2026_001" not in response.text
    assert PASSWORD not in response.text and "$argon2" not in response.text
    assert response.headers["cache-control"] == "no-store"
    with test_app.state.session_factory() as db:
        assert db.scalar(select(User.password_hash)) not in response.text


def test_short_student_no_is_never_returned_in_full(client):
    register(client, "A-1")
    assert login(client, "A-1").status_code == 200
    assert client.get("/api/auth/me").json()["student_no_masked"] == "**1"


def test_logout_deletes_cookie_and_revokes_replayed_session(client, test_app):
    register(client)
    login(client)
    token = client.cookies.get("scut_share_session")
    response = client.post("/api/auth/logout", headers=ORIGIN)
    assert response.status_code == 204 and response.content == b""
    assert "max-age=0" in response.headers["set-cookie"].lower()
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Cookie": f"scut_share_session={token}"}).status_code == 401
    with test_app.state.session_factory() as db:
        assert db.get(AuthSession, token_hash(token)) is None


def test_expired_session_cannot_be_used(client, test_app):
    register(client)
    login(client)
    with test_app.state.session_factory() as db:
        db.execute(update(AuthSession).values(expires_at=datetime.now(UTC) - timedelta(seconds=1)))
        db.commit()
    assert client.get("/api/auth/me").status_code == 401


def test_user_sessions_are_isolated(client, test_app):
    first = register(client, "ACCOUNT_A", "甲同学").json()
    second = register(client, "ACCOUNT_B", "乙同学").json()
    login(client, "ACCOUNT_A")
    token_a = client.cookies.get("scut_share_session")
    with TestClient(test_app) as other:
        login(other, "ACCOUNT_B")
        token_b = other.cookies.get("scut_share_session")
        assert token_a != token_b
        assert client.get(f"/api/auth/me?user_id={second['id']}").json()["id"] == first["id"]
        assert other.get(f"/api/auth/me?user_id={first['id']}").json()["id"] == second["id"]
        client.post("/api/auth/logout", headers=ORIGIN)
        assert other.get("/api/auth/me").status_code == 200


@pytest.mark.parametrize("origin", [None, "https://example.com", "http://localhost:5174", "null"])
def test_untrusted_origin_cannot_logout_using_valid_cookie(client, origin):
    register(client)
    login(client)
    headers = {"Origin": origin} if origin else {}
    response = client.post("/api/auth/logout", headers=headers)
    assert response.status_code == 403
    assert "set-cookie" not in response.headers
    assert client.get("/api/auth/me").status_code == 200


@pytest.mark.parametrize("path", ["register", "login"])
def test_login_and_registration_also_require_origin(client, path):
    response = client.post(f"/api/auth/{path}", json={
        "student_no": "ACCOUNT_A", "password": PASSWORD, "nickname": "测试同学", "campus": "五山校区",
    })
    assert response.status_code == 403


def test_relogin_rotates_and_invalidates_old_token(client):
    register(client)
    login(client)
    previous_token = client.cookies.get("scut_share_session")
    assert login(client).status_code == 200
    assert client.cookies.get("scut_share_session") != previous_token
    assert client.get("/api/auth/me", headers={"Cookie": f"scut_share_session={previous_token}"}).status_code == 401


def test_credentials_cors_preflight_for_post(client):
    response = client.options("/api/auth/login", headers={
        **ORIGIN, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "Content-Type",
    })
    assert response.status_code == 200
    assert response.headers["access-control-allow-credentials"] == "true"
    assert response.headers["access-control-allow-origin"] == ORIGIN["Origin"]


def test_tampered_session_token_is_rejected(client):
    register(client)
    login(client)
    assert client.get("/api/auth/me", headers={"Cookie": "scut_share_session=invalid"}).status_code == 401
