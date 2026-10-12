"""Add independent free borrowing records and active-only unique indexes."""
from alembic import op
import sqlalchemy as sa

revision = "20261012_04"
down_revision = "20261012_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "borrow_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("borrower_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("requested_start_at", sa.DateTime(), nullable=False),
        sa.Column("expected_return_at", sa.DateTime(), nullable=False),
        sa.Column("note", sa.String(300), nullable=True),
        sa.Column("status", sa.String(14), server_default="pending", nullable=False),
        sa.Column("owner_handover_confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("borrower_handover_confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("owner_return_confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("borrower_return_confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("borrowed_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'approved', 'borrowed', 'return_pending', 'completed', 'rejected', 'canceled')", name="borrow_status"),
        sa.CheckConstraint("owner_id != borrower_id", name="borrow_different_users"),
        sa.CheckConstraint("expected_return_at > requested_start_at", name="borrow_time_order"),
        sa.CheckConstraint("status NOT IN ('borrowed', 'return_pending', 'completed') OR (owner_handover_confirmed_at IS NOT NULL AND borrower_handover_confirmed_at IS NOT NULL AND borrowed_at IS NOT NULL)", name="borrow_handover"),
        sa.CheckConstraint("status != 'completed' OR (owner_return_confirmed_at IS NOT NULL AND borrower_return_confirmed_at IS NOT NULL AND completed_at IS NOT NULL)", name="borrow_completion"),
    )
    for column in ("item_id", "owner_id", "borrower_id"):
        op.create_index(f"ix_borrow_requests_{column}", "borrow_requests", [column])
    op.create_index("uq_borrow_item_active", "borrow_requests", ["item_id"], unique=True, sqlite_where=sa.text("status IN ('approved', 'borrowed', 'return_pending')"))
    op.create_index("uq_borrow_user_active", "borrow_requests", ["item_id", "borrower_id"], unique=True, sqlite_where=sa.text("status IN ('pending', 'approved', 'borrowed', 'return_pending')"))


def downgrade() -> None:
    op.drop_table("borrow_requests")
