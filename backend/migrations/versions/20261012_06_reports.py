"""Add local admin role, scoped reports and single appeals."""
from alembic import op
import sqlalchemy as sa

revision = "20261012_06"
down_revision = "20261012_05"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="0"))
    op.create_table("reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reporter_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("target_type", sa.String(7), nullable=False), sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(100), nullable=False), sa.Column("description", sa.String(2000), nullable=False),
        sa.Column("evidence_json", sa.Text(), nullable=False), sa.Column("status", sa.String(9), nullable=False, server_default="pending"),
        sa.Column("resolution_note", sa.String(1000)), sa.Column("reviewer_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.Column("resolved_at", sa.DateTime()), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.CheckConstraint("target_type IN ('item', 'trade', 'borrow', 'message')", name="report_target"),
        sa.CheckConstraint("target_id > 0", name="report_target_id"),
        sa.CheckConstraint("status IN ('pending', 'handled', 'dismissed')", name="report_status"),
        sa.CheckConstraint("status = 'pending' OR (resolution_note IS NOT NULL AND resolved_at IS NOT NULL AND reviewer_id IS NOT NULL)", name="report_resolution"))
    op.create_index("ix_reports_reporter_id", "reports", ["reporter_id"])
    op.create_index("ix_reports_status_created", "reports", ["status", "created_at"])
    op.create_table("report_appeals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("report_id", sa.Integer(), sa.ForeignKey("reports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reason", sa.String(1000), nullable=False), sa.Column("status", sa.String(8), nullable=False, server_default="pending"),
        sa.Column("decision", sa.String(9)), sa.Column("review_note", sa.String(1000)),
        sa.Column("reviewer_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()), sa.Column("reviewed_at", sa.DateTime()),
        sa.UniqueConstraint("report_id", name="uq_report_appeal_once"),
        sa.CheckConstraint("status IN ('pending', 'reviewed')", name="appeal_status"),
        sa.CheckConstraint("status = 'pending' OR (decision IN ('handled', 'dismissed') AND review_note IS NOT NULL AND reviewed_at IS NOT NULL AND reviewer_id IS NOT NULL)", name="appeal_review"))


def downgrade():
    op.drop_table("report_appeals")
    op.drop_table("reports")
    op.drop_column("users", "is_admin")
