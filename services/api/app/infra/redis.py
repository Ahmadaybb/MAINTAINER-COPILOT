from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Any

from redis import Redis


class RedisAdapter:
    def __init__(self, url: str | None = None) -> None:
        self.client = Redis.from_url(url or os.getenv("REDIS_URL", "redis://redis:6379/0"), decode_responses=True)

    def load_short_term_memory(self, session_id: str) -> list[dict[str, Any]]:
        raw = self.client.get(f"stm:{session_id}")
        if not raw:
            return []
        return json.loads(raw)

    def save_short_term_memory(
        self,
        session_id: str,
        messages: list[Mapping[str, Any]],
        ttl_seconds: int = 3600,
    ) -> None:
        self.client.setex(f"stm:{session_id}", ttl_seconds, json.dumps(messages, default=str))

    def increment_rate_limit(self, user_id: str, window: str, ttl_seconds: int) -> int:
        key = f"rl:{user_id}:{window}"
        pipe = self.client.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl_seconds, nx=True)
        count, _ = pipe.execute()
        return int(count)
