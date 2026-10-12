from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.item import PublicOwner
from app.schemas.trade import TradeItemResponse


class GiftCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note: str | None = Field(default=None, max_length=300)

    @field_validator("note")
    @classmethod
    def strip(cls, value):
        return value.strip() or None if value is not None else None


class GiftResponse(BaseModel):
    id: int
    item_id: int
    owner_id: int
    recipient_id: int
    note: str | None
    status: Literal["pending", "approved", "rejected", "canceled", "completed"]
    owner_confirmed_at: datetime | None
    recipient_confirmed_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    item: TradeItemResponse
    owner: PublicOwner
    recipient: PublicOwner

    @field_validator("owner_confirmed_at", "recipient_confirmed_at", "completed_at", "created_at", "updated_at")
    @classmethod
    def utc(cls, value):
        return value.replace(tzinfo=UTC) if value is not None and value.tzinfo is None else value


class GiftList(BaseModel):
    gifts: list[GiftResponse]
    total: int
    page: int
    page_size: int
