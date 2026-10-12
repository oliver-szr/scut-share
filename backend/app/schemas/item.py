from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

from app.core.constants import Campus, InterestTag, ItemCategory, ItemMode, ItemStatus

Title = Annotated[str, Field(min_length=2, max_length=100)]
Description = Annotated[str, Field(min_length=1, max_length=4000)]
BorrowNote = Annotated[str, Field(min_length=1, max_length=1000)]
PriceCents = Annotated[StrictInt, Field(gt=0, le=100_000_000)]


def validate_tags(tags: list[InterestTag]) -> list[InterestTag]:
    if tags is None or len(tags) > 8 or len(set(tags)) != len(tags):
        raise ValueError("兴趣标签最多选择 8 个且不能重复")
    return tags


class ItemFields(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Title
    description: Description
    category: ItemCategory
    mode: ItemMode
    campus: Campus
    price_cents: PriceCents | None = None
    borrow_note: BorrowNote | None = None
    interest_tags: list[InterestTag] = Field(default_factory=list)

    _tags = field_validator("interest_tags")(validate_tags)

    @field_validator("title", "description", "borrow_note", mode="before")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_mode_fields(self):
        if self.mode is ItemMode.SALE:
            if self.price_cents is None:
                raise ValueError("二手出售物品必须设置大于 0 的售价")
            if self.borrow_note is not None:
                raise ValueError("二手出售物品不能设置借用说明")
        elif self.price_cents is not None:
            raise ValueError("免费借还和免费转赠物品不能设置售价")
        if self.mode is ItemMode.GIFT and self.borrow_note is not None:
            raise ValueError("免费转赠物品不能设置借用说明")
        return self


class ItemCreate(ItemFields):
    pass


class ItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Title | None = None
    description: Description | None = None
    category: ItemCategory | None = None
    mode: ItemMode | None = None
    campus: Campus | None = None
    price_cents: PriceCents | None = None
    borrow_note: BorrowNote | None = None
    interest_tags: list[InterestTag] | None = None

    _tags = field_validator("interest_tags")(validate_tags)


class PublicOwner(BaseModel):
    id: int
    nickname: str


class ItemImageResponse(BaseModel):
    id: int
    url: str
    content_type: str


class ItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    owner_id: int
    title: str
    description: str
    category: ItemCategory
    mode: ItemMode
    campus: Campus
    price_cents: int | None
    borrow_note: str | None
    status: ItemStatus
    availability: Literal["available", "reserved", "sold", "gifted", "borrowed", "return_pending", "unavailable"]
    interest_tags: list[str]
    images: list[ItemImageResponse]
    owner: PublicOwner
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class ItemListResponse(BaseModel):
    items: list[ItemResponse]
    total: int
    page: int
    page_size: int
