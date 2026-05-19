from __future__ import annotations

from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import require_admin
from app.domain.memory import LongTermMemoryRead
from app.domain.user import AuthenticatedUser

if TYPE_CHECKING:
    from app.services.long_term_memory import LongTermMemoryService

router = APIRouter(prefix="/api/v1/admin/memory", tags=["admin-memory"])


def get_long_term_memory_service() -> LongTermMemoryService:
    from app.services.long_term_memory import LongTermMemoryService

    return LongTermMemoryService()


@router.get("", response_model=list[LongTermMemoryRead])
async def inspect_memory(
    owner_id: UUID,
    _admin: Annotated[AuthenticatedUser, Depends(require_admin)],
    service: Annotated[LongTermMemoryService, Depends(get_long_term_memory_service)],
) -> list[LongTermMemoryRead]:
    return service.list_active(owner_id=owner_id)
