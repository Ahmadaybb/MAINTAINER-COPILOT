from __future__ import annotations

import os
import time
from uuid import UUID

from app.domain.errors import RateLimited
from app.infra.redis import RedisAdapter


class RateLimiter:
    def __init__(
        self,
        redis: RedisAdapter | None = None,
        limit: int | None = None,
        window_seconds: int | None = None,
    ) -> None:
        self.redis = redis or RedisAdapter()
        self.limit = limit or int(os.getenv("TRIAGE_RATE_LIMIT", "30"))
        self.window_seconds = window_seconds or int(os.getenv("TRIAGE_RATE_WINDOW_SECONDS", "60"))

    def check(self, user_id: UUID) -> None:
        window = str(int(time.time() // self.window_seconds))
        count = self.redis.increment_rate_limit(str(user_id), window, self.window_seconds)
        if count > self.limit:
            raise RateLimited("Please try again shortly.")
