#GitHub repo → docs/issues → chunks → embeddings → pgvector

from __future__ import annotations

from app.domain.knowledge import KnowledgeSourceCreate, KnowledgeSourceRead
from app.infra.embeddings import DEFAULT_EMBEDDING_MODEL, EmbeddingClient
from app.infra.github_ingest import GitHubIngestClient
from app.infra.redaction import redact_text
from app.repositories.chunks import DocumentChunkRepository
from app.repositories.db import get_sessionmaker
from app.repositories.knowledge import KnowledgeSourceRepository, source_to_domain
from app.repositories.models.knowledge import KnowledgeSourceStatus
from app.services.chunking import Chunker


class KnowledgeSourceService:
    def __init__(
        self,
        *,
        github: GitHubIngestClient | None = None,
        embeddings: EmbeddingClient | None = None,
        chunker: Chunker | None = None,
    ) -> None:
        self.github = github or GitHubIngestClient()
        self.embeddings = embeddings or EmbeddingClient()
        self.chunker = chunker or Chunker()

    async def connect(self, payload: KnowledgeSourceCreate) -> KnowledgeSourceRead:
        with get_sessionmaker()() as session:
            repo = KnowledgeSourceRepository(session)
            source = repo.replace_single(
                github_repo=payload.github_repo,
                branch=payload.branch,
                docs_globs=payload.docs_globs,
            )
            session.commit()
            source_id = source.id

        await self.sync(source_id)
        return self.get_current()

    def get_current(self) -> KnowledgeSourceRead:
        with get_sessionmaker()() as session:
            source = KnowledgeSourceRepository(session).get_active()
            if not source:
                from app.domain.errors import NotFoundError

                raise NotFoundError("No knowledge source is connected.")
            return source_to_domain(source)

    async def sync_current(self) -> KnowledgeSourceRead:
        current = self.get_current()
        await self.sync(current.id)
        return self.get_current()

    async def sync(self, source_id) -> None:
        with get_sessionmaker()() as session:
            source_repo = KnowledgeSourceRepository(session)
            source = source_repo.get_by_id(source_id)
            if not source:
                from app.domain.errors import NotFoundError

                raise NotFoundError("No knowledge source is connected.")
            source_repo.set_status(source, KnowledgeSourceStatus.SYNCING)
            session.commit()
            source_data = source_to_domain(source)

        try:
            documents = await self.github.ingest(
                source_data.github_repo,
                source_data.branch,
                source_data.docs_globs,
            )
            chunks = self.chunker.chunk(
                source_id=source_data.id,
                documents=documents,
                embedding_model=DEFAULT_EMBEDDING_MODEL,
            )
            embeddings = self.embeddings.embed([chunk.content for chunk in chunks])
            for chunk, embedding in zip(chunks, embeddings, strict=True):
                chunk.embedding = embedding

            with get_sessionmaker()() as session:
                source_repo = KnowledgeSourceRepository(session)
                source = source_repo.get_by_id(source_data.id)
                if source:
                    DocumentChunkRepository(session).replace_for_source(source_data.id, chunks)
                    source_repo.set_status(source, KnowledgeSourceStatus.READY, synced=True)
                session.commit()
        except Exception as exc:  # noqa: BLE001 - service converts sync failure to state.
            with get_sessionmaker()() as session:
                source_repo = KnowledgeSourceRepository(session)
                source = source_repo.get_by_id(source_data.id)
                if source:
                    source_repo.set_status(
                        source,
                        KnowledgeSourceStatus.ERROR,
                        last_error=redact_text(str(exc)),
                    )
                session.commit()
