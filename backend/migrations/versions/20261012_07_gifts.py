"""Extend item mode safely and add independent free gift requests."""
from alembic import op
import sqlalchemy as sa

revision = "20261012_07"
down_revision = "20261012_06"
branch_labels = None
depends_on = None

OLD_FIELDS = "(mode = 'sale' AND price_cents > 0 AND borrow_note IS NULL) OR (mode = 'borrow' AND price_cents IS NULL)"
NEW_FIELDS = "(mode = 'sale' AND price_cents IS NOT NULL AND price_cents > 0 AND borrow_note IS NULL) OR (mode = 'borrow' AND price_cents IS NULL) OR (mode = 'gift' AND price_cents IS NULL AND borrow_note IS NULL)"


def upgrade():
    # env.py uses a dedicated FK-disabled, transactional migration connection.
    # This prevents DROP of the old items table from cascading to item_images.
    with op.batch_alter_table("items", recreate="always") as batch:
        batch.drop_constraint("item_mode", type_="check")
        batch.drop_constraint("item_mode_fields", type_="check")
        batch.create_check_constraint("item_mode", "mode IN ('sale', 'borrow', 'gift')")
        batch.create_check_constraint("item_mode_fields", NEW_FIELDS)
    op.create_table("gift_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("recipient_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("note", sa.String(300)), sa.Column("status", sa.String(9), server_default="pending", nullable=False),
        sa.Column("owner_confirmed_at", sa.DateTime()), sa.Column("recipient_confirmed_at", sa.DateTime()), sa.Column("completed_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected', 'canceled', 'completed')", name="gift_status"),
        sa.CheckConstraint("owner_id != recipient_id", name="gift_different_users"),
        sa.CheckConstraint("status != 'completed' OR (owner_confirmed_at IS NOT NULL AND recipient_confirmed_at IS NOT NULL AND completed_at IS NOT NULL)", name="gift_completion"))
    for name in ("item_id", "owner_id", "recipient_id"):
        op.create_index(f"ix_gift_requests_{name}", "gift_requests", [name])
    op.create_index("uq_gift_item_committed", "gift_requests", ["item_id"], unique=True, sqlite_where=sa.text("status IN ('approved', 'completed')"))
    op.create_index("uq_gift_recipient_active", "gift_requests", ["item_id", "recipient_id"], unique=True, sqlite_where=sa.text("status IN ('pending', 'approved')"))


def downgrade():
    if op.get_bind().execute(sa.text("SELECT COUNT(*) FROM items WHERE mode='gift'")).scalar() or op.get_bind().execute(sa.text("SELECT COUNT(*) FROM gift_requests")).scalar():
        raise RuntimeError("存在转赠数据，拒绝删除；请保留数据库并使用备份恢复。")
    op.drop_table("gift_requests")
    with op.batch_alter_table("items", recreate="always") as batch:
        batch.drop_constraint("item_mode", type_="check")
        batch.drop_constraint("item_mode_fields", type_="check")
        batch.create_check_constraint("item_mode", "mode IN ('sale', 'borrow')")
        batch.create_check_constraint("item_mode_fields", OLD_FIELDS)
