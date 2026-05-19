from __future__ import annotations

from uuid import UUID

from app.infra.redis import RedisAdapter


class ShortTermMemory:
    def __init__(self, redis: RedisAdapter | None = None, ttl_seconds: int = 3600) -> None:
        self.redis = redis or RedisAdapter()
        self.ttl_seconds = ttl_seconds

    def load(self, session_id: UUID) -> list[dict]:
        return self.redis.load_short_term_memory(str(session_id))

    def append(self, session_id: UUID, message: dict) -> list[dict]:
        messages = self.load(session_id)
        messages.append(message)
        self.redis.save_short_term_memory(str(session_id), messages, ttl_seconds=self.ttl_seconds)
        return messages
