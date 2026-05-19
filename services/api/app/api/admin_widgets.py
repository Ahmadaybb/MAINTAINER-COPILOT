from __future__ import annotations

from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import require_admin
from app.domain.user import AuthenticatedUser
from app.domain.widget import WidgetConfigCreate, WidgetConfigRead, WidgetConfigUpdate

if TYPE_CHECKING:
    from app.services.widget_config_service import WidgetConfigService

router = APIRouter(prefix="/api/v1/admin/widgets", tags=["admin-widgets"])


def get_widget_config_service() -> WidgetConfigService:
    from app.services.widget_config_service import WidgetConfigService

    return WidgetConfigService()


@router.post("", response_model=WidgetConfigRead, status_code=status.HTTP_201_CREATED)
async def create_widget_config(
    payload: WidgetConfigCreate,
    admin: Annotated[AuthenticatedUser, Depends(require_admin)],
    service: Annotated[WidgetConfigService, Depends(get_widget_config_service)],
) -> WidgetConfigRead:
    return service.create(payload, created_by=admin.id)


@router.get("", response_model=list[WidgetConfigRead])
async def list_widget_configs(
    _admin: Annotated[AuthenticatedUser, Depends(require_admin)],
    service: Annotated[WidgetConfigService, Depends(get_widget_config_service)],
) -> list[WidgetConfigRead]:
    return service.list()


@router.get("/{widget_id}", response_model=WidgetConfigRead)
async def get_widget_config(
    widget_id: UUID,
    _admin: Annotated[AuthenticatedUser, Depends(require_admin)],
    service: Annotated[WidgetConfigService, Depends(get_widget_config_service)],
) -> WidgetConfigRead:
    return service.get(widget_id)


@router.put("/{widget_id}", response_model=WidgetConfigRead)
async def update_widget_config(
    widget_id: UUID,
    payload: WidgetConfigUpdate,
    _admin: Annotated[AuthenticatedUser, Depends(require_admin)],
    service: Annotated[WidgetConfigService, Depends(get_widget_config_service)],
) -> WidgetConfigRead:
    return service.update(widget_id, payload)
