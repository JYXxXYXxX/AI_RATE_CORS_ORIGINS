"""add_cnki_report_support

Revision ID: 20250512_add_cnki_report
Revises: 20250511_add_blocks
Create Date: 2025-05-12 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20250512_add_cnki_report"
down_revision: Union[str, None] = "20250511_add_blocks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Extend analysis_runs with mode column
    op.add_column("analysis_runs", sa.Column("mode", sa.String(length=20), server_default="estimate", nullable=True))

    # 2. Extend document_blocks with report_risk JSONB
    op.add_column("document_blocks", sa.Column("report_risk", postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # 3. Create cnki_reports table
    op.create_table(
        "cnki_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("report_type", sa.String(length=30), nullable=False),
        sa.Column("filename", sa.String(length=500), nullable=True),
        sa.Column("raw_format", sa.String(length=20), nullable=True),
        sa.Column("total_copy_ratio", sa.Float(), nullable=True),
        sa.Column("aigc_ratio", sa.Float(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("parsed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=True),
        sa.Column("status", sa.String(length=20), server_default="parsed", nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["analysis_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_cnki_reports_doc", "cnki_reports", ["document_id"])
    op.create_index("idx_cnki_reports_run", "cnki_reports", ["run_id"])

    # 4. Create cnki_report_spans table
    op.create_table(
        "cnki_report_spans",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("span_id", sa.String(length=64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("risk_type", sa.String(length=30), nullable=False),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column("similarity", sa.Float(), nullable=True),
        sa.Column("aigc_score", sa.Float(), nullable=True),
        sa.Column("matched_source", sa.Text(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("raw_meta", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=True),
        sa.ForeignKeyConstraint(["report_id"], ["cnki_reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_id", "span_id"),
    )
    op.create_index("idx_cnki_spans_report", "cnki_report_spans", ["report_id"])
    op.create_index("idx_cnki_spans_risk", "cnki_report_spans", ["report_id", "risk_level"])

    # 5. Create block_report_mappings table
    op.create_table(
        "block_report_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("block_id", sa.String(length=64), nullable=False),
        sa.Column("span_id", sa.String(length=64), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("match_method", sa.String(length=20), nullable=False),
        sa.Column("match_confidence", sa.Float(), nullable=False),
        sa.Column("matched_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["report_id"], ["cnki_reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "block_id", "span_id"),
    )
    op.create_index("idx_block_mappings_doc", "block_report_mappings", ["document_id", "block_id"])
    op.create_index("idx_block_mappings_span", "block_report_mappings", ["report_id", "span_id"])


def downgrade() -> None:
    op.drop_index("idx_block_mappings_span", table_name="block_report_mappings")
    op.drop_index("idx_block_mappings_doc", table_name="block_report_mappings")
    op.drop_table("block_report_mappings")

    op.drop_index("idx_cnki_spans_risk", table_name="cnki_report_spans")
    op.drop_index("idx_cnki_spans_report", table_name="cnki_report_spans")
    op.drop_table("cnki_report_spans")

    op.drop_index("idx_cnki_reports_run", table_name="cnki_reports")
    op.drop_index("idx_cnki_reports_doc", table_name="cnki_reports")
    op.drop_table("cnki_reports")

    op.drop_column("document_blocks", "report_risk")
    op.drop_column("analysis_runs", "mode")
