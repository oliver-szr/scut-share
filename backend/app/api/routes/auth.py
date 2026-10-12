import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import AuthenticatedUser, DbSession, read_session_token, require_trusted_origin
from app.core.security import hash_password, mask_student_no, password_hasher, token_hash, verify_password
from app.models.auth_session import AuthSession
from app.models.user import User
from app.schemas.auth import CurrentUser, LoginRequest, PublicUser, RegisterRequest

router = APIRouter(prefix="/auth", tags=["auth"])
trusted_origin = [Depends(require_trusted_origin)]


def private_user(user: User) -> CurrentUser:
    return CurrentUser(
        **PublicUser.model_validate(user).model_dump(),
        student_no_masked=mask_student_no(user.student_no),
        is_admin=user.is_admin,
    )


@router.post("/register", response_model=PublicUser, status_code=201, dependencies=trusted_origin)
def register(payload: RegisterRequest, db: DbSession, response: Response) -> PublicUser:
    if db.scalar(select(User.id).where(User.student_no == payload.student_no)) is not None:
        raise HTTPException(status_code=409, detail="该学号已注册，请登录或使用其他账号。")
    user = User(
        nickname=payload.nickname, student_no=payload.student_no, campus=payload.campus,
        password_hash=hash_password(payload.password.get_secret_value()),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # The database unique constraint also covers concurrent registration.
        raise HTTPException(status_code=409, detail="该学号已注册，请登录或使用其他账号。") from None
    db.refresh(user)
    response.headers["Cache-Control"] = "no-store"
    return PublicUser.model_validate(user)


@router.post("/login", response_model=CurrentUser, dependencies=trusted_origin)
def login(payload: LoginRequest, request: Request, response: Response, db: DbSession) -> CurrentUser:
    user = db.scalar(select(User).where(User.student_no == payload.student_no))
    password = payload.password.get_secret_value()
    valid = verify_password(password, user.password_hash if user else None)
    if user is None or not valid:
        raise HTTPException(status_code=401, detail="学号或密码错误。")
    if password_hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)

    now = datetime.now(UTC)
    config = request.app.state.settings
    previous_token = read_session_token(request)
    if previous_token:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash(previous_token)))
    db.execute(delete(AuthSession).where(AuthSession.expires_at <= now))
    token = secrets.token_urlsafe(32)
    expires = now + timedelta(seconds=config.session_ttl_seconds)
    db.add(AuthSession(token_hash=token_hash(token), user_id=user.id, expires_at=expires))
    db.commit()
    response.set_cookie(
        key=config.session_cookie_name, value=token, max_age=config.session_ttl_seconds,
        expires=expires, httponly=True, secure=config.session_cookie_secure,
        samesite="lax", path="/api",
    )
    response.headers["Cache-Control"] = "no-store"
    return private_user(user)


@router.post("/logout", status_code=204, dependencies=trusted_origin)
def logout(request: Request, db: DbSession) -> Response:
    token = read_session_token(request)
    if token:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash(token)))
        db.commit()
    config = request.app.state.settings
    response = Response(status_code=204, headers={"Cache-Control": "no-store"})
    response.delete_cookie(
        key=config.session_cookie_name, path="/api", httponly=True,
        secure=config.session_cookie_secure, samesite="lax",
    )
    return response


@router.get("/me", response_model=CurrentUser)
def me(user: AuthenticatedUser, response: Response) -> CurrentUser:
    response.headers["Cache-Control"] = "no-store"
    return private_user(user)
