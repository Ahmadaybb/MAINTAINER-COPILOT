from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domain.knowledge import KnowledgeSourceRead
from app.repositories.models.knowledge import KnowledgeSource, KnowledgeSourceStatus


class KnowledgeSourceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_active(self) -> KnowledgeSource | None:
        statement = select(KnowledgeSource).order_by(KnowledgeSource.created_at.desc()).limit(1)
        return self.session.execute(statement).scalar_one_or_none()

    def get_by_id(self, source_id: UUID) -> KnowledgeSource | None:
        return self.session.get(KnowledgeSource, source_id)

    def replace_single(
        self,
        *,
        github_repo: str,
        branch: str,
        docs_globs: list[str],
    ) -> KnowledgeSource:
        self.session.execute(delete(KnowledgeSource))
        source = KnowledgeSource(
            github_repo=github_repo,
            branch=branch,
            docs_globs=docs_globs,
            status=KnowledgeSourceStatus.CONNECTING,
        )
        self.session.add(source)
        self.session.flush()
        return source

    def set_status(
        self,
        source: KnowledgeSource,
        status: KnowledgeSourceStatus,
        *,
        last_error: str | None = None,
        synced: bool = False,
    ) -> KnowledgeSource:
        source.status = status
        source.last_error = last_error
        if synced:
            source.last_synced_at = datetime.now(UTC)
        self.session.flush()
        return source


def source_to_domain(source: KnowledgeSource) -> KnowledgeSourceRead:
    return KnowledgeSourceRead(
        id=source.id,
        github_repo=source.github_repo,
        branch=source.branch,
        docs_globs=list(source.docs_globs),
        status=source.status.value,
        last_synced_at=source.last_synced_at,
        last_error=source.last_error,
    )
