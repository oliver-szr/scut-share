from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class TradeIntent(Base):
    __tablename__ = "trade_intents"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'reserved', 'rejected', 'canceled', 'completed')", name="trade_status"),
        CheckConstraint("buyer_id != seller_id", name="trade_different_users"),
        CheckConstraint("price_cents_snapshot > 0 AND price_cents_snapshot <= 100000000", name="trade_price"),
        CheckConstraint("status != 'completed' OR (buyer_confirmed_at IS NOT NULL AND seller_confirmed_at IS NOT NULL AND completed_at IS NOT NULL)", name="trade_completion"),
        Index("uq_trade_item_committed", "item_id", unique=True, sqlite_where=text("status IN ('reserved', 'completed')")),
        Index("uq_trade_buyer_active", "item_id", "buyer_id", unique=True, sqlite_where=text("status IN ('pending', 'reserved')")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="RESTRICT"), index=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    price_cents_snapshot: Mapped[int]
    note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    status: Mapped[str] = mapped_column(String(9), default="pending", server_default="pending")
    buyer_confirmed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    seller_confirmed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp(), onupdate=lambda: datetime.now(UTC))
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    item = relationship("Item")
    buyer = relationship("User", foreign_keys=[buyer_id])
    seller = relationship("User", foreign_keys=[seller_id])
