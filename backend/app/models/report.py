from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint("target_type IN ('item', 'trade', 'borrow', 'message')", name="report_target"),
        CheckConstraint("target_id > 0", name="report_target_id"),
        CheckConstraint("status IN ('pending', 'handled', 'dismissed')", name="report_status"),
        CheckConstraint("status = 'pending' OR (resolution_note IS NOT NULL AND resolved_at IS NOT NULL AND reviewer_id IS NOT NULL)", name="report_resolution"),
        Index("ix_reports_status_created", "status", "created_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    target_type: Mapped[str] = mapped_column(String(7))
    target_id: Mapped[int]
    reason: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(2000))
    evidence_json: Mapped[str] = mapped_column(Text())
    status: Mapped[str] = mapped_column(String(9), default="pending", server_default="pending")
    resolution_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp(), onupdate=lambda: datetime.now(UTC))
    appeal: Mapped["ReportAppeal | None"] = relationship(back_populates="report", uselist=False)


class ReportAppeal(Base):
    __tablename__ = "report_appeals"
    __table_args__ = (
        UniqueConstraint("report_id", name="uq_report_appeal_once"),
        CheckConstraint("status IN ('pending', 'reviewed')", name="appeal_status"),
        CheckConstraint("status = 'pending' OR (decision IN ('handled', 'dismissed') AND review_note IS NOT NULL AND reviewed_at IS NOT NULL AND reviewer_id IS NOT NULL)", name="appeal_review"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id", ondelete="RESTRICT"))
    reason: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(8), default="pending", server_default="pending")
    decision: Mapped[str | None] = mapped_column(String(9), nullable=True)
    review_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp())
    reviewed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    report: Mapped[Report] = relationship(back_populates="appeal")
