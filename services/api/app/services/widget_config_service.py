from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any
from uuid import UUID

from app.domain.errors import NotFoundError
from app.domain.widget import PublicWidgetConfig, WidgetConfigCreate, WidgetConfigRead, WidgetConfigUpdate

if TYPE_CHECKING:
    from app.repositories.widgets import WidgetConfigRepository


EMPTY_ORIGINS_WARNING = "This widget will not load anywhere until at least one allowed origin is added."
EMBED_SNIPPET_TEMPLATE = '<script src="/widget.js" data-widget-id="{widget_id}" async></script>'


class WidgetConfigService:
    def __init__(
        self,
        *,
        sessionmaker: Callable[[], Any] | None = None,
        repository_factory: Callable[[Any], WidgetConfigRepository] | None = None,
    ) -> None:
        self._sessionmaker = sessionmaker
        self._repository_factory = repository_factory

    def create(self, payload: WidgetConfigCreate, *, created_by: UUID) -> WidgetConfigRead:
        with self._session() as session:
            config = self._repo(session).create(
                name=payload.name,
                theme=payload.theme,
                allowed_origins=payload.allowed_origins,
                greeting=payload.greeting,
                enabled_tools=payload.enabled_tools,
                host_token_verify_key=payload.host_token_verify_key,
                created_by=created_by,
            )
            session.commit()
            return self._to_domain(config)

    def list(self) -> list[WidgetConfigRead]:
        with self._session() as session:
            return [self._to_domain(config) for config in self._repo(session).list()]

    def get(self, widget_id: UUID) -> WidgetConfigRead:
        with self._session() as session:
            config = self._repo(session).get(widget_id)
            if config is None:
                raise NotFoundError("Widget configuration was not found.")
            return self._to_domain(config)

    def update(self, widget_id: UUID, payload: WidgetConfigUpdate) -> WidgetConfigRead:
        with self._session() as session:
            repo = self._repo(session)
            config = repo.get(widget_id)
            if config is None:
                raise NotFoundError("Widget configuration was not found.")
            updated = repo.update(
                config,
                name=payload.name,
                theme=payload.theme,
                allowed_origins=payload.allowed_origins,
                greeting=payload.greeting,
                enabled_tools=payload.enabled_tools,
                host_token_verify_key=payload.host_token_verify_key,
            )
            session.commit()
            return self._to_domain(updated)

    def _session(self):
        if self._sessionmaker is not None:
            return self._sessionmaker()
        from app.repositories.db import get_sessionmaker

        return get_sessionmaker()()

    def _repo(self, session) -> WidgetConfigRepository:
        if self._repository_factory is not None:
            return self._repository_factory(session)
        from app.repositories.widgets import WidgetConfigRepository

        return WidgetConfigRepository(session)

    def _to_domain(self, config) -> WidgetConfigRead:
        allowed_origins = list(config.allowed_origins or [])
        return WidgetConfigRead(
            id=config.id,
            name=config.name,
            theme=dict(config.theme or {}),
            allowed_origins=allowed_origins,
            greeting=config.greeting,
            enabled_tools=list(config.enabled_tools or []),
            host_token_verify_key=config.host_token_verify_key,
            created_by=config.created_by,
            created_at=config.created_at,
            embed_snippet=EMBED_SNIPPET_TEMPLATE.format(widget_id=config.id),
            warnings=[EMPTY_ORIGINS_WARNING] if not allowed_origins else [],
        )


def public_widget_config(config: WidgetConfigRead) -> PublicWidgetConfig:
    return PublicWidgetConfig(
        theme=config.theme,
        greeting=config.greeting,
        enabled_tools=config.enabled_tools,
    )


def widget_origin_policy_headers(
    *,
    allowed_origins: list[str],
    request_origin: str | None,
) -> dict[str, str]:
    frame_ancestors = " ".join(allowed_origins) if allowed_origins else "'none'"
    headers = {
        "Content-Security-Policy": f"frame-ancestors {frame_ancestors}",
        "Vary": "Origin",
    }
    if request_origin and request_origin in allowed_origins:
        headers["Access-Control-Allow-Origin"] = request_origin
    return headers
