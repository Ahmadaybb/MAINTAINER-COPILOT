from __future__ import annotations

import asyncio
from dataclasses import dataclass
from uuid import uuid4

from app.domain.knowledge import DocumentChunk, DocumentKind, RagQuery
from app.services.rag_service import RagService


@dataclass(slots=True)
class RetrievedChunk:
    chunk: DocumentChunk
    score: float


class FakeRetrieval:
    def __init__(self, chunks: list[RetrievedChunk]) -> None:
        self.chunks = chunks

    async def search(self, *, source_id, question, filters):
        return self.chunks


class FakeAnthropic:
    async def complete(self, *, system_prompt: str, user_prompt: str, max_tokens: int = 500) -> str:
        return "Use the documented retry policy for transient API failures."


def test_rag_answer_cites_at_least_one_source_when_grounded() -> None:
    asyncio.run(_assert_grounded_answer())


async def _assert_grounded_answer() -> None:
    source_id = uuid4()
    chunk = DocumentChunk(
        id=uuid4(),
        source_id=source_id,
        kind=DocumentKind.DOC,
        external_ref="docs/retries.md",
        title="Retry policy",
        content="Transient API failures should be retried with backoff.",
        chunk_index=0,
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
    )
    service = RagService(
        retrieval=FakeRetrieval([RetrievedChunk(chunk=chunk, score=0.99)]),
        anthropic=FakeAnthropic(),
        source_id_override=source_id,
    )

    response = await service.answer(RagQuery(question="How do we handle transient API failures?"))

    assert response.grounded is True
    assert response.citations
    assert response.citations[0].external_ref == "docs/retries.md"
    assert "retry" in response.answer.lower()


def test_rag_answer_declines_when_ungrounded() -> None:
    asyncio.run(_assert_ungrounded_answer())


async def _assert_ungrounded_answer() -> None:
    service = RagService(
        retrieval=FakeRetrieval([]),
        anthropic=FakeAnthropic(),
        source_id_override=uuid4(),
    )

    response = await service.answer(RagQuery(question="What is the private roadmap?"))

    assert response.grounded is False
    assert response.citations == []
    assert "not have enough grounded material" in response.answer
