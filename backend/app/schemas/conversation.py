from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.item import ItemImageResponse, PublicOwner


class ConversationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1, max_length=1000)

    @field_validator("content", mode="before")
    @classmethod
    def strip_content(cls, value):
        return value.strip() if isinstance(value, str) else value


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    conversation_id: int
    sender_id: int
    content: str
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def utc_timestamp(cls, value):
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class ConversationItemResponse(BaseModel):
    id: int
    title: str
    images: list[ItemImageResponse]


class ConversationResponse(BaseModel):
    id: int
    context_type: Literal["sale_item", "borrow_request"]
    item_id: int
    borrow_request_id: int | None
    other_user: PublicOwner
    item: ConversationItemResponse
    last_message: MessageResponse | None
    last_message_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", "last_message_at")
    @classmethod
    def utc_timestamp(cls, value):
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]
    total: int
    page: int
    page_size: int


class MessageListResponse(BaseModel):
    messages: list[MessageResponse]
    has_more: bool
