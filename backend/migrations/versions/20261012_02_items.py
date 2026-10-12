"""Create Phase 2 item and item image tables."""
from alembic import op
import sqlalchemy as sa

revision = "20261012_02"
down_revision = "20261012_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(10), nullable=False),
        sa.Column("mode", sa.String(6), nullable=False),
        sa.Column("campus", sa.String(6), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=True),
        sa.Column("borrow_note", sa.String(1000), nullable=True),
        sa.Column("status", sa.String(9), server_default="published", nullable=False),
        sa.Column("interest_tags_json", sa.String(512), server_default="[]", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.CheckConstraint("category IN ('教材资料', '数码配件', '生活用品', '运动户外', '兴趣娱乐', '其他')", name="item_category"),
        sa.CheckConstraint("mode IN ('sale', 'borrow')", name="item_mode"),
        sa.CheckConstraint("campus IN ('五山校区', '大学城校区', '广州国际校区')", name="item_campus"),
        sa.CheckConstraint("status IN ('published', 'withdrawn')", name="item_status"),
        sa.CheckConstraint("(mode = 'sale' AND price_cents > 0 AND borrow_note IS NULL) OR (mode = 'borrow' AND price_cents IS NULL)", name="item_mode_fields"),
    )
    op.create_index("ix_items_owner_id", "items", ["owner_id"])
    op.create_index("ix_items_public_listing", "items", ["status", "created_at"])
    op.create_index("ix_items_filters", "items", ["mode", "category", "campus"])
    op.create_table(
        "item_images",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_name", sa.String(128), nullable=False),
        sa.Column("content_type", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.UniqueConstraint("file_name", name="uq_item_images_file_name"),
    )
    op.create_index("ix_item_images_item_id", "item_images", ["item_id"])


def downgrade() -> None:
    op.drop_index("ix_item_images_item_id", table_name="item_images")
    op.drop_table("item_images")
    op.drop_index("ix_items_filters", table_name="items")
    op.drop_index("ix_items_public_listing", table_name="items")
    op.drop_index("ix_items_owner_id", table_name="items")
    op.drop_table("items")
