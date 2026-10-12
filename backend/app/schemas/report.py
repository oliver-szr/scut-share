from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
ReportStatus = Literal["pending", "handled", "dismissed"]


class ReportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_type: Literal["item", "trade", "borrow", "message"]
    target_id: int = Field(gt=0, strict=True)
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    description: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class AppealCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: ShortText


class ResolutionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["handled", "dismissed"]
    note: ShortText


class AppealResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    reason: str
    status: Literal["pending", "reviewed"]
    decision: Literal["handled", "dismissed"] | None
    review_note: str | None
    created_at: datetime
    reviewed_at: datetime | None

    @field_validator("created_at", "reviewed_at")
    @classmethod
    def utc(cls, value):
        return value.replace(tzinfo=UTC) if value is not None and value.tzinfo is None else value


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    target_type: str
    target_id: int
    reason: str
    description: str
    status: ReportStatus
    resolution_note: str | None
    created_at: datetime
    resolved_at: datetime | None
    appeal: AppealResponse | None

    @field_validator("created_at", "resolved_at")
    @classmethod
    def utc(cls, value):
        return value.replace(tzinfo=UTC) if value is not None and value.tzinfo is None else value


class ReportDetail(ReportResponse):
    evidence: dict


class ReportList(BaseModel):
    reports: list[ReportResponse]
    total: int
    page: int
    page_size: int
