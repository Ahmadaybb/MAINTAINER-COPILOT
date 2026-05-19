from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from app.domain.errors import NotFoundError, ToolFailure
from app.domain.knowledge import Citation, RagAnswer, RagQuery
from app.infra.anthropic import AnthropicClient

if TYPE_CHECKING:
    from app.services.retrieval import RetrievalService


class RagService:
    def __init__(
        self,
        *,
        retrieval: RetrievalService | None = None,
        anthropic: AnthropicClient | None = None,
        source_id_override: UUID | None = None,
    ) -> None:
        if retrieval is None:
            from app.services.retrieval import RetrievalService

            retrieval = RetrievalService()
        self.retrieval = retrieval
        self.anthropic = anthropic or AnthropicClient()
        self.source_id_override = source_id_override

    async def answer(self, query: RagQuery) -> RagAnswer:
        source_id = self.source_id_override or self._active_source_id()

        retrieved = await self.retrieval.search(
            source_id=source_id,
            question=query.question,
            filters=query.filters,
        )
        if not retrieved:
            return RagAnswer(answer="I do not have enough grounded material to answer that.", grounded=False)

        context = "\n\n".join(
            f"[{index + 1}] {item.chunk.title} ({item.chunk.external_ref})\n{item.chunk.content}"
            for index, item in enumerate(retrieved)
        )
        prompt = (
            "Answer only from the supplied context. If the context is insufficient, say there is no grounding.\n\n"
            f"Question: {query.question}\n\nContext:\n{context}"
        )
        try:
            answer = await self.anthropic.complete(
                system_prompt="You answer repository maintenance questions with citations.",
                user_prompt=prompt,
                max_tokens=600,
            )
        except ToolFailure:
            answer = _extractive_answer(query.question, [item.chunk.content for item in retrieved])

        citations = [
            Citation(
                external_ref=item.chunk.external_ref,
                kind=item.chunk.kind,
                title=item.chunk.title,
            )
            for item in retrieved[:3]
        ]
        return RagAnswer(answer=answer, citations=citations, grounded=bool(citations))

    def _active_source_id(self) -> UUID:
        from app.repositories.db import get_sessionmaker
        from app.repositories.knowledge import KnowledgeSourceRepository

        with get_sessionmaker()() as session:
            source = KnowledgeSourceRepository(session).get_active()
            if not source:
                raise NotFoundError("No knowledge source is connected.")
            return source.id


def _extractive_answer(_question: str, contexts: list[str]) -> str:
    first = " ".join(contexts[0].split())
    return first[:500] if first else "I do not have enough grounded material to answer that."
