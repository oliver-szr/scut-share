from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import token_hash
from app.db.session import get_session
from app.models.auth_session import AuthSession
from app.models.user import User

DbSession = Annotated[Session, Depends(get_session)]


def require_trusted_origin(request: Request) -> None:
    if request.headers.get("origin") not in request.app.state.settings.cors_origins:
        raise HTTPException(status_code=403, detail="请求来源不受信任，请从本站页面操作。")


def read_session_token(request: Request) -> str | None:
    token = request.cookies.get(request.app.state.settings.session_cookie_name)
    return token if token and len(token) <= 128 else None


def get_current_user(request: Request, db: DbSession) -> User:
    token = read_session_token(request)
    if token:
        user = db.scalar(select(User).join(AuthSession, AuthSession.user_id == User.id).where(
            AuthSession.token_hash == token_hash(token),
            AuthSession.expires_at > datetime.now(UTC),
        ))
        if user is not None:
            return user
    raise HTTPException(status_code=401, detail="登录已失效，请重新登录。")


AuthenticatedUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: AuthenticatedUser) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="仅管理员可以访问。")
    return user


AdminUser = Annotated[User, Depends(require_admin)]
