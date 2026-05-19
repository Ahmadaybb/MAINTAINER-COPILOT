from __future__ import annotations

from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response

from app.domain.widget import PublicWidgetConfig
from app.services.widget_config_service import public_widget_config, widget_origin_policy_headers

if TYPE_CHECKING:
    from app.domain.widget import WidgetConfigRead
    from app.services.widget_config_service import WidgetConfigService

router = APIRouter(prefix="/api/v1/widgets", tags=["widgets"])


def get_widget_config_service() -> WidgetConfigService:
    from app.services.widget_config_service import WidgetConfigService

    return WidgetConfigService()


@router.get("/{widget_id}/config", response_model=PublicWidgetConfig)
async def get_widget_config(
    widget_id: UUID,
    response: Response,
    service: Annotated[WidgetConfigService, Depends(get_widget_config_service)],
    origin: Annotated[str | None, Header()] = None,
) -> PublicWidgetConfig:
    config = service.get(widget_id)
    for header, value in widget_origin_policy_headers(
        allowed_origins=config.allowed_origins,
        request_origin=origin,
    ).items():
        response.headers[header] = value
    return public_widget_config(config)
