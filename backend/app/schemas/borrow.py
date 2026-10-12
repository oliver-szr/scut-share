from datetime import UTC, datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.item import ItemImageResponse, PublicOwner

BorrowStatus = Literal["pending", "approved", "borrowed", "return_pending", "completed", "rejected", "canceled"]


class BorrowRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requested_start_at: AwareDatetime
    expected_return_at: AwareDatetime
    note: str | None = Field(default=None, max_length=300)

    @field_validator("requested_start_at", "expected_return_at", mode="before")
    @classmethod
    def require_datetime(cls, value):
        if not isinstance(value, (str, datetime)):
            raise ValueError("时间必须是带时区的日期时间")
        return value

    @field_validator("requested_start_at", "expected_return_at")
    @classmethod
    def normalize_utc(cls, value):
        return value.astimezone(UTC)

    @field_validator("note")
    @classmethod
    def strip_note(cls, value):
        return value.strip() or None if value is not None else None

    @model_validator(mode="after")
    def valid_time_order(self):
        if self.expected_return_at <= self.requested_start_at:
            raise ValueError("预计归还时间必须晚于预计开始时间")
        return self


class BorrowItemResponse(BaseModel):
    id: int
    title: str
    images: list[ItemImageResponse]


class BorrowResponse(BaseModel):
    id: int
    item_id: int
    owner_id: int
    borrower_id: int
    requested_start_at: datetime
    expected_return_at: datetime
    note: str | None
    status: BorrowStatus
    owner_handover_confirmed_at: datetime | None
    borrower_handover_confirmed_at: datetime | None
    owner_return_confirmed_at: datetime | None
    borrower_return_confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    borrowed_at: datetime | None
    completed_at: datetime | None
    item: BorrowItemResponse
    owner: PublicOwner
    borrower: PublicOwner

    @field_validator("requested_start_at", "expected_return_at", "owner_handover_confirmed_at", "borrower_handover_confirmed_at",
                     "owner_return_confirmed_at", "borrower_return_confirmed_at", "created_at", "updated_at", "borrowed_at", "completed_at")
    @classmethod
    def utc_timestamp(cls, value):
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class BorrowListResponse(BaseModel):
    borrows: list[BorrowResponse]
    total: int
    page: int
    page_size: int
