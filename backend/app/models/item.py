import json
from datetime import UTC, datetime

from sqlalchemy import Enum, ForeignKey, Index, Integer, String, Text, func, select
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship

from app.core.constants import Campus, ItemCategory, ItemMode, ItemStatus
from app.db.session import Base
from app.models.trade_intent import TradeIntent
from app.models.borrow_request import BorrowRequest
from app.models.gift_request import GiftRequest


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (
        Index("ix_items_public_listing", "status", "created_at"),
        Index("ix_items_filters", "mode", "category", "campus"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text())
    category: Mapped[ItemCategory] = mapped_column(String(10))
    mode: Mapped[ItemMode] = mapped_column(Enum(
        ItemMode, values_callable=lambda enum: [item.value for item in enum],
        native_enum=False, create_constraint=True, name="item_mode",
    ))
    campus: Mapped[Campus] = mapped_column(Enum(
        Campus, values_callable=lambda enum: [item.value for item in enum],
        native_enum=False, create_constraint=True, name="item_campus",
    ))
    price_cents: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    borrow_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[ItemStatus] = mapped_column(Enum(
        ItemStatus, values_callable=lambda enum: [item.value for item in enum],
        native_enum=False, create_constraint=True, name="item_status",
    ), default=ItemStatus.PUBLISHED, server_default=ItemStatus.PUBLISHED.value)
    interest_tags_json: Mapped[str] = mapped_column(String(512), default="[]", server_default="[]")
    created_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.current_timestamp(), onupdate=lambda: datetime.now(UTC),
    )

    owner = relationship("User")
    trade_state = column_property(
        select(TradeIntent.status).where(
            TradeIntent.item_id == id, TradeIntent.status.in_(["reserved", "completed"]),
        ).correlate_except(TradeIntent).scalar_subquery()
    )
    borrow_state = column_property(
        select(BorrowRequest.status).where(
            BorrowRequest.item_id == id, BorrowRequest.status.in_(["approved", "borrowed", "return_pending"]),
        ).correlate_except(BorrowRequest).scalar_subquery()
    )
    gift_state = column_property(select(GiftRequest.status).where(GiftRequest.item_id == id, GiftRequest.status.in_(["approved", "completed"])).correlate_except(GiftRequest).scalar_subquery())

    @property
    def availability(self) -> str:
        if self.status == ItemStatus.WITHDRAWN:
            return "unavailable"
        if self.mode == ItemMode.BORROW:
            return {"approved": "reserved", "borrowed": "borrowed", "return_pending": "return_pending"}.get(self.borrow_state, "available")
        if self.mode == ItemMode.GIFT:
            return {"approved": "reserved", "completed": "gifted"}.get(self.gift_state, "available")
        return {"reserved": "reserved", "completed": "sold"}.get(self.trade_state, "available")

    images: Mapped[list["ItemImage"]] = relationship(
        back_populates="item", cascade="all, delete-orphan", order_by="ItemImage.created_at",
    )

    @property
    def interest_tags(self) -> list[str]:
        try:
            value = json.loads(self.interest_tags_json or "[]")
        except (TypeError, ValueError):
            return []
        return value if isinstance(value, list) else []

    def set_interest_tags(self, tags: list[str]) -> None:
        self.interest_tags_json = json.dumps(tags, ensure_ascii=False, separators=(",", ":"))


class ItemImage(Base):
    __tablename__ = "item_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), index=True)
    file_name: Mapped[str] = mapped_column(String(128), unique=True)
    content_type: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp())

    item: Mapped[Item] = relationship(back_populates="images")
