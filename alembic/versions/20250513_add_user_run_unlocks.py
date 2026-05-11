"""add_user_run_unlocks

Revision ID: 20250513_add_unlocks
Revises: 20250512_add_cnki_report
Create Date: 2025-05-13 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20250513_add_unlocks"
down_revision: Union[str, None] = "20250512_add_cnki_report"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_run_unlocks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_no", sa.String(length=80), nullable=False),
        sa.Column("package_code", sa.String(length=50), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="pending_payment", nullable=False),
        sa.Column("payment_method", sa.String(length=30), nullable=True),
        sa.Column("screenshot_path", sa.String(length=500), nullable=True),
        sa.Column("screenshot_url", sa.String(length=500), nullable=True),
        sa.Column("reviewed_by", sa.String(length=100), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["app_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_no"),
    )
    op.create_index("idx_unlocks_user_run", "user_run_unlocks", ["user_id", "run_id", "package_code"], unique=True)
    op.create_index("idx_unlocks_status", "user_run_unlocks", ["status", "created_at"])
    op.create_index("idx_unlocks_run", "user_run_unlocks", ["run_id"])


def downgrade() -> None:
    op.drop_index("idx_unlocks_run", table_name="user_run_unlocks")
    op.drop_index("idx_unlocks_status", table_name="user_run_unlocks")
    op.drop_index("idx_unlocks_user_run", table_name="user_run_unlocks")
    op.drop_table("user_run_unlocks")
