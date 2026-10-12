"""Create Phase 3 trade intents without changing existing item or account rows."""
from alembic import op
import sqlalchemy as sa

revision = "20261012_03"
down_revision = "20261012_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trade_intents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("buyer_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("seller_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("price_cents_snapshot", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(300), nullable=True),
        sa.Column("status", sa.String(9), server_default="pending", nullable=False),
        sa.Column("buyer_confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("seller_confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'reserved', 'rejected', 'canceled', 'completed')", name="trade_status"),
        sa.CheckConstraint("buyer_id != seller_id", name="trade_different_users"),
        sa.CheckConstraint("price_cents_snapshot > 0 AND price_cents_snapshot <= 100000000", name="trade_price"),
        sa.CheckConstraint("status != 'completed' OR (buyer_confirmed_at IS NOT NULL AND seller_confirmed_at IS NOT NULL AND completed_at IS NOT NULL)", name="trade_completion"),
    )
    for column in ("item_id", "buyer_id", "seller_id"):
        op.create_index(f"ix_trade_intents_{column}", "trade_intents", [column])
    op.create_index("uq_trade_item_committed", "trade_intents", ["item_id"], unique=True, sqlite_where=sa.text("status IN ('reserved', 'completed')"))
    op.create_index("uq_trade_buyer_active", "trade_intents", ["item_id", "buyer_id"], unique=True, sqlite_where=sa.text("status IN ('pending', 'reserved')"))


def downgrade() -> None:
    op.drop_table("trade_intents")
