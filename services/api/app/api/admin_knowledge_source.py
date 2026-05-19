from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import require_admin
from app.domain.knowledge import KnowledgeSourceCreate, KnowledgeSourceRead
from app.domain.user import AuthenticatedUser
from app.services.knowledge_source_service import KnowledgeSourceService

router = APIRouter(prefix="/api/v1/admin/knowledge-source", tags=["admin-knowledge-source"])


def get_knowledge_source_service() -> KnowledgeSourceService:
    return KnowledgeSourceService()


@router.post("", response_model=KnowledgeSourceRead, status_code=status.HTTP_201_CREATED)
async def connect_knowledge_source(
    payload: KnowledgeSourceCreate,
    _admin: Annotated[AuthenticatedUser, Depends(require_admin)],
    service: Annotated[KnowledgeSourceService, Depends(get_knowledge_source_service)],
) -> KnowledgeSourceRead:
    return await service.connect(payload)


@router.get("", response_model=KnowledgeSourceRead)
async def get_knowledge_source(
    _admin: Annotated[AuthenticatedUser, Depends(require_admin)],
    service: Annotated[KnowledgeSourceService, Depends(get_knowledge_source_service)],
) -> KnowledgeSourceRead:
    return service.get_current()


@router.post("/sync", response_model=KnowledgeSourceRead)
async def sync_knowledge_source(
    _admin: Annotated[AuthenticatedUser, Depends(require_admin)],
    service: Annotated[KnowledgeSourceService, Depends(get_knowledge_source_service)],
) -> KnowledgeSourceRead:
    return await service.sync_current()
