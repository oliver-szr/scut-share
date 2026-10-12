from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class GiftRequest(Base):
    __tablename__ = "gift_requests"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'approved', 'rejected', 'canceled', 'completed')", name="gift_status"),
        CheckConstraint("owner_id != recipient_id", name="gift_different_users"),
        CheckConstraint("status != 'completed' OR (owner_confirmed_at IS NOT NULL AND recipient_confirmed_at IS NOT NULL AND completed_at IS NOT NULL)", name="gift_completion"),
        Index("uq_gift_item_committed", "item_id", unique=True, sqlite_where=text("status IN ('approved', 'completed')")),
        Index("uq_gift_recipient_active", "item_id", "recipient_id", unique=True, sqlite_where=text("status IN ('pending', 'approved')")),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="RESTRICT"), index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    status: Mapped[str] = mapped_column(String(9), default="pending", server_default="pending")
    owner_confirmed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    recipient_confirmed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp(), onupdate=lambda: datetime.now(UTC))
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    item = relationship("Item")
    owner = relationship("User", foreign_keys=[owner_id])
    recipient = relationship("User", foreign_keys=[recipient_id])
