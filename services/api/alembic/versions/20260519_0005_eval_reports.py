"""create eval report table

Revision ID: 20260519_0005
Revises: 20260519_0004
Create Date: 2026-05-19
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260519_0005"
down_revision = "20260519_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    eval_kind = postgresql.ENUM("classification", "rag", name="eval_kind")
    eval_kind.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "eval_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", eval_kind, nullable=False),
        sa.Column("commit_sha", sa.Text(), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("minio_key", sa.Text(), nullable=False),
        sa.Column("previous_report_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["previous_report_id"], ["eval_reports.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_eval_reports_kind_created_at", "eval_reports", ["kind", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_eval_reports_kind_created_at", table_name="eval_reports")
    op.drop_table("eval_reports")
    postgresql.ENUM(name="eval_kind").drop(op.get_bind(), checkfirst=True)
