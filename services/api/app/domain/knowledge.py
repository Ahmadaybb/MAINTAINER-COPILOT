from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeSourceStatus(StrEnum):
    CONNECTING = "connecting"
    READY = "ready"
    SYNCING = "syncing"
    ERROR = "error"


class DocumentKind(StrEnum):
    DOC = "doc"
    RESOLVED_ISSUE = "resolved_issue"


class KnowledgeSourceCreate(BaseModel):
    github_repo: str = Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
    branch: str = "main"
    docs_globs: list[str] = Field(default_factory=lambda: ["README*", "docs/**"])


class KnowledgeSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    github_repo: str
    branch: str
    docs_globs: list[str]
    status: KnowledgeSourceStatus
    last_synced_at: datetime | None = None
    last_error: str | None = None


class DocumentChunk(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    source_id: UUID
    kind: DocumentKind
    external_ref: str
    title: str
    content: str
    chunk_index: int
    issue_type: str | None = None
    issue_date: date | None = None
    resolution_status: str | None = None
    embedding: list[float] | None = None
    embedding_model: str


class RetrievalFilters(BaseModel):
    issue_type: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    resolution_status: str | None = None


class Citation(BaseModel):
    external_ref: str
    kind: DocumentKind
    title: str


class RagQuery(BaseModel):
    question: str = Field(min_length=1)
    filters: RetrievalFilters = Field(default_factory=RetrievalFilters)


class RagAnswer(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    grounded: bool
