"""add_email_verification

Revision ID: 20260520_add_email_verification
Revises: 20250513_add_internal_risk
Create Date: 2026-05-20 12:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260520_add_email_verification"
down_revision: Union[str, None] = "20250513_add_internal_risk"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "app_users",
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "app_users",
        sa.Column("verification_email_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("UPDATE app_users SET email_verified_at = now() WHERE email_verified_at IS NULL")

    op.create_table(
        "user_email_verification_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["app_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "idx_user_email_verification_user_id",
        "user_email_verification_tokens",
        ["user_id", "created_at"],
    )
    op.create_index(
        "idx_user_email_verification_expires_at",
        "user_email_verification_tokens",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_user_email_verification_expires_at",
        table_name="user_email_verification_tokens",
    )
    op.drop_index(
        "idx_user_email_verification_user_id",
        table_name="user_email_verification_tokens",
    )
    op.drop_table("user_email_verification_tokens")
    op.drop_column("app_users", "verification_email_sent_at")
    op.drop_column("app_users", "email_verified_at")

