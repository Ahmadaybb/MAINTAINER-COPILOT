from __future__ import annotations

from functools import cached_property


DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSIONS = 384


class EmbeddingClient:
    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL) -> None:
        self.model_name = model_name

    @cached_property
    def model(self):
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(self.model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self.model.encode(texts, normalize_embeddings=True)
        return [list(map(float, vector)) for vector in vectors]

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]
