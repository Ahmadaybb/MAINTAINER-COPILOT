from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from uuid import UUID

from app.domain.knowledge import DocumentChunk, RetrievalFilters
from app.infra.anthropic import AnthropicClient
from app.infra.embeddings import EmbeddingClient
from app.repositories.chunks import DocumentChunkRepository
from app.repositories.db import get_sessionmaker


HYDE_PROMPT_PATH = Path(__file__).resolve().parents[4] / "prompts" / "hyde.md"


@dataclass(slots=True)
class RetrievedChunk:
    chunk: DocumentChunk
    score: float


class RetrievalService:
    def __init__(
        self,
        *,
        embeddings: EmbeddingClient | None = None,
        anthropic: AnthropicClient | None = None,
        alpha: float = 0.65,
        top_k: int = 6,
        rerank_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    ) -> None:
        self.embeddings = embeddings or EmbeddingClient()
        self.anthropic = anthropic
        self.alpha = alpha
        self.top_k = top_k
        self.rerank_model_name = rerank_model_name

    @cached_property
    def reranker(self):
        from sentence_transformers import CrossEncoder

        return CrossEncoder(self.rerank_model_name)

    async def search(
        self,
        *,
        source_id: UUID,
        question: str,
        filters: RetrievalFilters,
    ) -> list[RetrievedChunk]:
        transformed_query = await self._hyde(question)
        query_embedding = self.embeddings.embed_one(transformed_query)
        with get_sessionmaker()() as session:
            repo = DocumentChunkRepository(session)
            all_chunks = _apply_filters(repo.list_for_source(source_id), filters)
            dense_chunks = repo.query_dense(
                source_id=source_id,
                embedding=query_embedding,
                filters=filters,
                limit=max(self.top_k * 3, 10),
            )

        sparse_scores = _bm25_scores(transformed_query, all_chunks)
        dense_rank = {chunk.id: index for index, chunk in enumerate(dense_chunks)}
        candidates = {chunk.id: chunk for chunk in dense_chunks}
        candidates.update({chunk.id: chunk for chunk, _score in sparse_scores[: self.top_k * 3]})

        scored: list[RetrievedChunk] = []
        for chunk_id, chunk in candidates.items():
            sparse = next((score for item, score in sparse_scores if item.id == chunk_id), 0.0)
            dense = 1.0 / (1.0 + dense_rank.get(chunk_id, len(dense_chunks) + 1))
            scored.append(RetrievedChunk(chunk=chunk, score=self.alpha * dense + (1 - self.alpha) * sparse))

        scored.sort(key=lambda item: item.score, reverse=True)
        return self._rerank(question, scored[: self.top_k])

    async def _hyde(self, question: str) -> str:
        if not self.anthropic:
            return question
        prompt = HYDE_PROMPT_PATH.read_text(encoding="utf-8")
        return await self.anthropic.complete(system_prompt=prompt, user_prompt=question, max_tokens=160)

    def _rerank(self, question: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        if not chunks:
            return chunks
        try:
            pairs = [(question, item.chunk.content) for item in chunks]
            scores = self.reranker.predict(pairs)
        except Exception:
            return chunks
        reranked = [
            RetrievedChunk(chunk=item.chunk, score=float(score))
            for item, score in zip(chunks, scores, strict=True)
        ]
        reranked.sort(key=lambda item: item.score, reverse=True)
        return reranked


def _bm25_scores(query: str, chunks: list[DocumentChunk]) -> list[tuple[DocumentChunk, float]]:
    from rank_bm25 import BM25Okapi

    if not chunks:
        return []
    tokenized = [_tokenize(chunk.content) for chunk in chunks]
    bm25 = BM25Okapi(tokenized)
    scores = bm25.get_scores(_tokenize(query))
    max_score = max(scores) if len(scores) else 0.0
    normalized = [
        (chunk, float(score / max_score) if max_score else 0.0)
        for chunk, score in zip(chunks, scores, strict=True)
    ]
    normalized.sort(key=lambda item: item[1], reverse=True)
    return normalized


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in text.split()]


def _apply_filters(chunks: list[DocumentChunk], filters: RetrievalFilters) -> list[DocumentChunk]:
    filtered = chunks
    if filters.issue_type:
        filtered = [chunk for chunk in filtered if chunk.issue_type == filters.issue_type]
    if filters.resolution_status:
        filtered = [chunk for chunk in filtered if chunk.resolution_status == filters.resolution_status]
    if filters.date_from:
        filtered = [chunk for chunk in filtered if chunk.issue_date and chunk.issue_date >= filters.date_from]
    if filters.date_to:
        filtered = [chunk for chunk in filtered if chunk.issue_date and chunk.issue_date <= filters.date_to]
    return filtered
