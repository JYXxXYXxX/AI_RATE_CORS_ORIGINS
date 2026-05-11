"""add_document_blocks_and_patches

Revision ID: 20250511_add_blocks
Revises: b058272e86c7
Create Date: 2025-05-11 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20250511_add_blocks"
down_revision: Union[str, None] = "b058272e86c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # document_blocks
    op.create_table(
        "document_blocks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("block_id", sa.String(length=64), nullable=False),
        sa.Column("block_type", sa.String(length=30), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("html", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("source_map", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=True),
        sa.Column("section_index", sa.Integer(), nullable=True),
        sa.Column("paragraph_index", sa.Integer(), nullable=True),
        sa.Column("section_title", sa.String(length=255), nullable=True),
        sa.Column("section_type", sa.String(length=50), nullable=True),
        sa.Column("char_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "block_id"),
    )
    op.create_index("idx_document_blocks_doc_order", "document_blocks", ["document_id", "display_order"])

    # document_patches
    op.create_table(
        "document_patches",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("block_id", sa.String(length=64), nullable=False),
        sa.Column("old_text", sa.Text(), nullable=False),
        sa.Column("new_text", sa.Text(), nullable=False),
        sa.Column("source_map", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_document_patches_doc_block", "document_patches", ["document_id", "block_id"])
    op.create_index("idx_document_patches_run", "document_patches", ["run_id"])

    # risk_score column on document_blocks (not in initial create because it may need pgvector or be nullable)
    op.add_column("document_blocks", sa.Column("risk_score", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_index("idx_document_patches_run", table_name="document_patches")
    op.drop_index("idx_document_patches_doc_block", table_name="document_patches")
    op.drop_table("document_patches")
    op.drop_index("idx_document_blocks_doc_order", table_name="document_blocks")
    op.drop_table("document_blocks")
