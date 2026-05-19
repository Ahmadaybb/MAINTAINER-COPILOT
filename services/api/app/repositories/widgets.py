from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.repositories.models.widget import WidgetConfig


class WidgetConfigRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        name: str,
        theme: dict,
        allowed_origins: list[str],
        greeting: str,
        enabled_tools: list[str],
        host_token_verify_key: str,
        created_by: UUID,
    ) -> WidgetConfig:
        config = WidgetConfig(
            name=name,
            theme=theme,
            allowed_origins=allowed_origins,
            greeting=greeting,
            enabled_tools=enabled_tools,
            host_token_verify_key=host_token_verify_key,
            created_by=created_by,
        )
        self.session.add(config)
        self.session.flush()
        return config

    def list(self) -> list[WidgetConfig]:
        statement = select(WidgetConfig).order_by(WidgetConfig.created_at.desc())
        return list(self.session.execute(statement).scalars())

    def get(self, widget_id: UUID) -> WidgetConfig | None:
        return self.session.get(WidgetConfig, widget_id)

    def update(
        self,
        config: WidgetConfig,
        *,
        name: str | None = None,
        theme: dict | None = None,
        allowed_origins: list[str] | None = None,
        greeting: str | None = None,
        enabled_tools: list[str] | None = None,
        host_token_verify_key: str | None = None,
    ) -> WidgetConfig:
        updates = {
            "name": name,
            "theme": theme,
            "allowed_origins": allowed_origins,
            "greeting": greeting,
            "enabled_tools": enabled_tools,
            "host_token_verify_key": host_token_verify_key,
        }
        for field, value in updates.items():
            if value is not None:
                setattr(config, field, value)
        self.session.add(config)
        self.session.flush()
        return config

