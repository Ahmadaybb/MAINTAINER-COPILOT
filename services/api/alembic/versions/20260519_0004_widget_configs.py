"""create widget config table

Revision ID: 20260519_0004
Revises: 20260519_0003
Create Date: 2026-05-19
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260519_0004"
down_revision = "20260519_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "widget_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("theme", postgresql.JSONB(), nullable=False),
        sa.Column("allowed_origins", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("greeting", sa.Text(), nullable=False),
        sa.Column("enabled_tools", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("host_token_verify_key", sa.Text(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_widget_configs_created_by", "widget_configs", ["created_by"])
    op.create_foreign_key(
        "fk_conversation_sessions_widget_config_id_widget_configs",
        "conversation_sessions",
        "widget_configs",
        ["widget_config_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_conversation_sessions_widget_config_id_widget_configs",
        "conversation_sessions",
        type_="foreignkey",
    )
    op.drop_index("ix_widget_configs_created_by", table_name="widget_configs")
    op.drop_table("widget_configs")
