from __future__ import annotations

from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import require_user
from app.domain.memory import (
    ExplicitMemoryRequest,
    LongTermMemoryRead,
    MemoryDeleteResponse,
    MemoryWriteResponse,
)
from app.domain.user import AuthenticatedUser

if TYPE_CHECKING:
    from app.services.long_term_memory import LongTermMemoryService

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])


def get_long_term_memory_service() -> LongTermMemoryService:
    from app.services.long_term_memory import LongTermMemoryService

    return LongTermMemoryService()


@router.post("", response_model=MemoryWriteResponse)
async def write_memory(
    payload: ExplicitMemoryRequest,
    response: Response,
    user: Annotated[AuthenticatedUser, Depends(require_user)],
    service: Annotated[LongTermMemoryService, Depends(get_long_term_memory_service)],
) -> MemoryWriteResponse:
    result = service.write_memory_tool(
        owner_id=user.id,
        content=payload.content,
        supersedes_id=payload.supersedes_id,
    )
    if result.status == "stored":
        response.status_code = status.HTTP_201_CREATED
    return result


@router.get("", response_model=list[LongTermMemoryRead])
async def list_memories(
    user: Annotated[AuthenticatedUser, Depends(require_user)],
    service: Annotated[LongTermMemoryService, Depends(get_long_term_memory_service)],
) -> list[LongTermMemoryRead]:
    return service.list_active(owner_id=user.id)


@router.delete("/{memory_id}", response_model=MemoryDeleteResponse)
async def delete_memory(
    memory_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_user)],
    service: Annotated[LongTermMemoryService, Depends(get_long_term_memory_service)],
) -> MemoryDeleteResponse:
    service.delete(owner_id=user.id, memory_id=memory_id)
    return MemoryDeleteResponse(id=memory_id, deleted=True)
