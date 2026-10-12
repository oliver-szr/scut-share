from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class BorrowRequest(Base):
    __tablename__ = "borrow_requests"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'approved', 'borrowed', 'return_pending', 'completed', 'rejected', 'canceled')", name="borrow_status"),
        CheckConstraint("owner_id != borrower_id", name="borrow_different_users"),
        CheckConstraint("expected_return_at > requested_start_at", name="borrow_time_order"),
        CheckConstraint("status NOT IN ('borrowed', 'return_pending', 'completed') OR (owner_handover_confirmed_at IS NOT NULL AND borrower_handover_confirmed_at IS NOT NULL AND borrowed_at IS NOT NULL)", name="borrow_handover"),
        CheckConstraint("status != 'completed' OR (owner_return_confirmed_at IS NOT NULL AND borrower_return_confirmed_at IS NOT NULL AND completed_at IS NOT NULL)", name="borrow_completion"),
        Index("uq_borrow_item_active", "item_id", unique=True, sqlite_where=text("status IN ('approved', 'borrowed', 'return_pending')")),
        Index("uq_borrow_user_active", "item_id", "borrower_id", unique=True, sqlite_where=text("status IN ('pending', 'approved', 'borrowed', 'return_pending')")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="RESTRICT"), index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    borrower_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    requested_start_at: Mapped[datetime]
    expected_return_at: Mapped[datetime]
    note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    status: Mapped[str] = mapped_column(String(14), default="pending", server_default="pending")
    owner_handover_confirmed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    borrower_handover_confirmed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    owner_return_confirmed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    borrower_return_confirmed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp(), onupdate=lambda: datetime.now(UTC))
    borrowed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    item = relationship("Item")
    owner = relationship("User", foreign_keys=[owner_id])
    borrower = relationship("User", foreign_keys=[borrower_id])
