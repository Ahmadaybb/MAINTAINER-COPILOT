from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domain.knowledge import DocumentChunk as DomainChunk
from app.domain.knowledge import RetrievalFilters
from app.repositories.models.knowledge import DocumentChunk, DocumentKind


class DocumentChunkRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def replace_for_source(self, source_id: UUID, chunks: Sequence[DomainChunk]) -> None:
        self.session.execute(delete(DocumentChunk).where(DocumentChunk.source_id == source_id))
        for chunk in chunks:
            self.session.add(
                DocumentChunk(
                    source_id=source_id,
                    kind=DocumentKind(chunk.kind.value),
                    external_ref=chunk.external_ref,
                    title=chunk.title,
                    content=chunk.content,
                    chunk_index=chunk.chunk_index,
                    issue_type=chunk.issue_type,
                    issue_date=chunk.issue_date,
                    resolution_status=chunk.resolution_status,
                    embedding=chunk.embedding or [],
                    embedding_model=chunk.embedding_model,
                )
            )
        self.session.flush()

    def list_for_source(self, source_id: UUID) -> list[DomainChunk]:
        statement = select(DocumentChunk).where(DocumentChunk.source_id == source_id)
        return [chunk_to_domain(row) for row in self.session.execute(statement).scalars()]

    def query_dense(
        self,
        *,
        source_id: UUID,
        embedding: list[float],
        filters: RetrievalFilters,
        limit: int = 20,
    ) -> list[DomainChunk]:
        statement = select(DocumentChunk).where(DocumentChunk.source_id == source_id)
        if filters.issue_type:
            statement = statement.where(DocumentChunk.issue_type == filters.issue_type)
        if filters.resolution_status:
            statement = statement.where(DocumentChunk.resolution_status == filters.resolution_status)
        if filters.date_from:
            statement = statement.where(DocumentChunk.issue_date >= filters.date_from)
        if filters.date_to:
            statement = statement.where(DocumentChunk.issue_date <= filters.date_to)
        statement = statement.order_by(DocumentChunk.embedding.cosine_distance(embedding)).limit(limit)
        return [chunk_to_domain(row) for row in self.session.execute(statement).scalars()]


def chunk_to_domain(chunk: DocumentChunk) -> DomainChunk:
    return DomainChunk(
        id=chunk.id,
        source_id=chunk.source_id,
        kind=chunk.kind.value,
        external_ref=chunk.external_ref,
        title=chunk.title,
        content=chunk.content,
        chunk_index=chunk.chunk_index,
        issue_type=chunk.issue_type,
        issue_date=chunk.issue_date,
        resolution_status=chunk.resolution_status,
        embedding=list(chunk.embedding),
        embedding_model=chunk.embedding_model,
    )
