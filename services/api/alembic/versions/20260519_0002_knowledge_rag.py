"""create knowledge source and document chunks

Revision ID: 20260519_0002
Revises: 20260518_0001
Create Date: 2026-05-19
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "20260519_0002"
down_revision = "20260518_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    postgresql.ENUM(
        "connecting",
        "ready",
        "syncing",
        "error",
        name="knowledge_source_status",
    ).create(op.get_bind(), checkfirst=True)
    postgresql.ENUM("doc", "resolved_issue", name="document_kind").create(op.get_bind(), checkfirst=True)
    source_status = postgresql.ENUM(
        "connecting",
        "ready",
        "syncing",
        "error",
        name="knowledge_source_status",
        create_type=False,
    )
    document_kind = postgresql.ENUM("doc", "resolved_issue", name="document_kind", create_type=False)

    op.create_table(
        "knowledge_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("github_repo", sa.Text(), nullable=False),
        sa.Column("branch", sa.Text(), nullable=False, server_default="main"),
        sa.Column("docs_globs", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("status", source_status, nullable=False, server_default="connecting"),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", document_kind, nullable=False),
        sa.Column("external_ref", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("issue_type", sa.Text(), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("resolution_status", sa.Text(), nullable=True),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column("embedding_model", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["knowledge_sources.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_document_chunks_source_id", "document_chunks", ["source_id"])
    op.create_index("ix_document_chunks_external_ref", "document_chunks", ["external_ref"])


def downgrade() -> None:
    op.drop_index("ix_document_chunks_external_ref", table_name="document_chunks")
    op.drop_index("ix_document_chunks_source_id", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_table("knowledge_sources")
    postgresql.ENUM(name="document_kind").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="knowledge_source_status").drop(op.get_bind(), checkfirst=True)
