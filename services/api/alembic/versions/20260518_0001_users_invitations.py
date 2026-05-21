"""create users and invitations

Revision ID: 20260518_0001
Revises:
Create Date: 2026-05-18
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260518_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "citext"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')

    postgresql.ENUM("user", "admin", name="user_role").create(op.get_bind(), checkfirst=True)
    user_role = postgresql.ENUM("user", "admin", name="user_role", create_type=False)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("hashed_password", sa.Text(), nullable=True),
        sa.Column("role", user_role, nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("invited_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["invited_by"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_invitations_email", "invitations", ["email"])


def downgrade() -> None:
    op.drop_index("ix_invitations_email", table_name="invitations")
    op.drop_table("invitations")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    postgresql.ENUM(name="user_role").drop(op.get_bind(), checkfirst=True)
