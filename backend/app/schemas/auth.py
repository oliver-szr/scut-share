from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, SecretStr, StringConstraints, field_validator

from app.core.constants import Campus

StudentNo = Annotated[str, StringConstraints(
    strip_whitespace=True, min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_-]+$",
)]
Nickname = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=30)]


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nickname: Nickname
    student_no: StudentNo
    campus: Campus
    password: Annotated[SecretStr, Field(min_length=8, max_length=128)]


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    student_no: StudentNo
    password: Annotated[SecretStr, Field(min_length=1, max_length=128)]


class PublicUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nickname: str
    campus: Campus
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        # SQLite stores naive timestamps; every application timestamp is UTC.
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class CurrentUser(PublicUser):
    student_no_masked: str
    is_admin: bool = False
