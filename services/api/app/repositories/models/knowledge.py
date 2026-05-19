from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.repositories.models.base import Base


class KnowledgeSourceStatus(str, enum.Enum):
    CONNECTING = "connecting"
    READY = "ready"
    SYNCING = "syncing"
    ERROR = "error"


class DocumentKind(str, enum.Enum):
    DOC = "doc"
    RESOLVED_ISSUE = "resolved_issue"


class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    github_repo: Mapped[str] = mapped_column(Text(), nullable=False)
    branch: Mapped[str] = mapped_column(Text(), nullable=False, default="main", server_default="main")
    docs_globs: Mapped[list[str]] = mapped_column(ARRAY(Text()), nullable=False)
    status: Mapped[KnowledgeSourceStatus] = mapped_column(
        Enum(
            KnowledgeSourceStatus,
            name="knowledge_source_status",
            values_callable=lambda values: [item.value for item in values],
        ),
        nullable=False,
        default=KnowledgeSourceStatus.CONNECTING,
        server_default=KnowledgeSourceStatus.CONNECTING.value,
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[DocumentKind] = mapped_column(
        Enum(DocumentKind, name="document_kind", values_callable=lambda values: [item.value for item in values]),
        nullable=False,
    )
    external_ref: Mapped[str] = mapped_column(Text(), nullable=False)
    title: Mapped[str] = mapped_column(Text(), nullable=False)
    content: Mapped[str] = mapped_column(Text(), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer(), nullable=False)
    issue_type: Mapped[str | None] = mapped_column(Text(), nullable=True)
    issue_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    resolution_status: Mapped[str | None] = mapped_column(Text(), nullable=True)
    embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
    embedding_model: Mapped[str] = mapped_column(Text(), nullable=False)
