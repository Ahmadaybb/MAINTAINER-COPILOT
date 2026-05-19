"""create conversation and long-term memory tables

Revision ID: 20260519_0003
Revises: 20260519_0002
Create Date: 2026-05-19
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "20260519_0003"
down_revision = "20260519_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    message_role = postgresql.ENUM("user", "assistant", "tool", name="message_role")
    memory_source = postgresql.ENUM("inferred", "explicit", name="memory_source")
    message_role.create(op.get_bind(), checkfirst=True)
    memory_source.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "conversation_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("widget_config_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_conversation_sessions_user_id", "conversation_sessions", ["user_id"])

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", message_role, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tool_calls", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["session_id"], ["conversation_sessions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_messages_session_id", "messages", ["session_id"])

    op.create_table(
        "long_term_memory",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column("embedding_model", sa.Text(), nullable=False),
        sa.Column("source", memory_source, nullable=False),
        sa.Column("superseded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["superseded_by"], ["long_term_memory.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_long_term_memory_owner_id", "long_term_memory", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_long_term_memory_owner_id", table_name="long_term_memory")
    op.drop_table("long_term_memory")
    op.drop_index("ix_messages_session_id", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_conversation_sessions_user_id", table_name="conversation_sessions")
    op.drop_table("conversation_sessions")
    postgresql.ENUM(name="memory_source").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="message_role").drop(op.get_bind(), checkfirst=True)
