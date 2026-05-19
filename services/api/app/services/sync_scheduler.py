from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.services.knowledge_source_service import KnowledgeSourceService

logger = logging.getLogger(__name__)


class KnowledgeSyncScheduler:
    def __init__(
        self,
        service: KnowledgeSourceService | None = None,
        interval_minutes: int = 60,
    ) -> None:
        self.service = service or KnowledgeSourceService()
        self.interval_minutes = interval_minutes
        self.scheduler = AsyncIOScheduler()

    def start(self) -> None:
        self.scheduler.add_job(self._sync_current, "interval", minutes=self.interval_minutes)
        self.scheduler.start()

    async def _sync_current(self) -> None:
        try:
            await self.service.sync_current()
        except Exception:  # noqa: BLE001 - scheduler degrades by logging and retaining status.
            logger.exception("Scheduled knowledge source sync failed")

    def shutdown(self) -> None:
        self.scheduler.shutdown(wait=False)
