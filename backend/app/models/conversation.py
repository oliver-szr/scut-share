from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint("(context_type = 'sale_item' AND borrow_request_id IS NULL) OR (context_type = 'borrow_request' AND borrow_request_id IS NOT NULL)", name="conversation_context"),
        CheckConstraint("participant_a_id != participant_b_id", name="conversation_different_users"),
        Index("uq_conversation_sale_pair", "item_id", "participant_a_id", "participant_b_id", unique=True, sqlite_where=text("context_type = 'sale_item'")),
        Index("uq_conversation_borrow", "borrow_request_id", unique=True, sqlite_where=text("context_type = 'borrow_request'")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    context_type: Mapped[str] = mapped_column(String(14))
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="RESTRICT"), index=True)
    borrow_request_id: Mapped[int | None] = mapped_column(ForeignKey("borrow_requests.id", ondelete="RESTRICT"), nullable=True)
    participant_a_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    participant_b_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp())

    item = relationship("Item")
    participant_a = relationship("User", foreign_keys=[participant_a_id])
    participant_b = relationship("User", foreign_keys=[participant_b_id])


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("length(trim(content)) > 0 AND length(content) <= 1000", name="message_content"),
        Index("ix_messages_conversation_id_id", "conversation_id", "id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="RESTRICT"))
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    content: Mapped[str] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp())
