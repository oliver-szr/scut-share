"""Add private contextual conversations and persistent text messages."""
from alembic import op
import sqlalchemy as sa

revision = "20261012_05"
down_revision = "20261012_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("context_type", sa.String(14), nullable=False),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("borrow_request_id", sa.Integer(), sa.ForeignKey("borrow_requests.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("participant_a_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("participant_b_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.CheckConstraint("(context_type = 'sale_item' AND borrow_request_id IS NULL) OR (context_type = 'borrow_request' AND borrow_request_id IS NOT NULL)", name="conversation_context"),
        sa.CheckConstraint("participant_a_id != participant_b_id", name="conversation_different_users"),
    )
    for column in ("item_id", "participant_a_id", "participant_b_id"):
        op.create_index(f"ix_conversations_{column}", "conversations", [column])
    op.create_index("uq_conversation_sale_pair", "conversations", ["item_id", "participant_a_id", "participant_b_id"], unique=True, sqlite_where=sa.text("context_type = 'sale_item'"))
    op.create_index("uq_conversation_borrow", "conversations", ["borrow_request_id"], unique=True, sqlite_where=sa.text("context_type = 'borrow_request'"))
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("conversations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("sender_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.CheckConstraint("length(trim(content)) > 0 AND length(content) <= 1000", name="message_content"),
    )
    op.create_index("ix_messages_conversation_id_id", "messages", ["conversation_id", "id"])


def downgrade() -> None:
    op.drop_table("messages")
    op.drop_table("conversations")
