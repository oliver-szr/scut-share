from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.item import ItemImageResponse, PublicOwner

TradeStatus = Literal["pending", "reserved", "rejected", "canceled", "completed"]


class TradeIntentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note: str | None = Field(default=None, max_length=300)

    @field_validator("note")
    @classmethod
    def strip_note(cls, value):
        return value.strip() or None if value is not None else None


class TradeItemResponse(BaseModel):
    id: int
    title: str
    images: list[ItemImageResponse]


class TradeResponse(BaseModel):
    id: int
    item_id: int
    buyer_id: int
    seller_id: int
    price_cents_snapshot: int
    note: str | None
    status: TradeStatus
    buyer_confirmed_at: datetime | None
    seller_confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    item: TradeItemResponse
    buyer: PublicOwner
    seller: PublicOwner

    @field_validator("buyer_confirmed_at", "seller_confirmed_at", "created_at", "updated_at", "completed_at")
    @classmethod
    def utc_timestamp(cls, value):
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class TradeListResponse(BaseModel):
    trades: list[TradeResponse]
    total: int
    page: int
    page_size: int
