from __future__ import annotations

import base64
import hashlib
import hmac
import json
from collections.abc import Callable
from types import SimpleNamespace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from app.domain.errors import NotFoundError, UnauthorizedError
from app.domain.widget import (
    PublicWidgetConfig,
    WidgetConfigCreate,
    WidgetConfigRead,
    WidgetConfigUpdate,
    WidgetSessionRequest,
    WidgetSessionResponse,
)
from app.repositories.models.user import UserRole as OrmUserRole
from app.repositories.users import UserRepository

if TYPE_CHECKING:
    from app.repositories.widgets import WidgetConfigRepository


EMPTY_ORIGINS_WARNING = "This widget will not load anywhere until at least one allowed origin is added."
EMBED_SNIPPET_TEMPLATE = '<script src="/widget.js" data-widget-id="{widget_id}" async></script>'
GENERIC_WIDGET_AUTH_ERROR = "Widget authentication failed."


class WidgetConfigService:
    def __init__(
        self,
        *,
        sessionmaker: Callable[[], Any] | None = None,
        repository_factory: Callable[[Any], WidgetConfigRepository] | None = None,
        token_minter: Callable[[Any], str] | None = None,
    ) -> None:
        self._sessionmaker = sessionmaker
        self._repository_factory = repository_factory
        self._token_minter = token_minter

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

    def create_widget_session(self, payload: WidgetSessionRequest) -> WidgetSessionResponse:
        config = self.get(payload.widget_id)
        if not payload.host_token:
            raise UnauthorizedError(GENERIC_WIDGET_AUTH_ERROR)
        host_identity = verify_host_token(
            host_token=payload.host_token,
            verify_key=config.host_token_verify_key,
            widget_id=payload.widget_id,
        )
        try:
            subject = UUID(str(host_identity["sub"]))
            email = str(host_identity.get("email", f"widget-{subject}@example.com"))
        except Exception as exc:  # noqa: BLE001 - keep widget auth failures generic.
            raise UnauthorizedError(GENERIC_WIDGET_AUTH_ERROR) from exc
        user = self._ensure_widget_user(user_id=subject, email=email)
        return WidgetSessionResponse(access_token=self._mint_access_token(user))

    def _ensure_widget_user(self, *, user_id: UUID, email: str) -> Any:
        with self._session() as session:
            if not hasattr(session, "get") or not hasattr(session, "execute"):
                return SimpleNamespace(
                    id=user_id,
                    email=email,
                    role=SimpleNamespace(value=OrmUserRole.USER.value),
                    is_active=True,
                )
            users = UserRepository(session)
            user = users.get_by_id(user_id) or users.get_by_email(email)
            if user is None:
                user = users.create(
                    user_id=user_id,
                    email=email,
                    hashed_password=None,
                    role=OrmUserRole.USER,
                    is_active=True,
                )
            else:
                user.is_active = True
            session.commit()
            return SimpleNamespace(
                id=user.id,
                email=user.email,
                role=SimpleNamespace(value=user.role.value),
                is_active=user.is_active,
            )

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

    def _mint_access_token(self, user: Any) -> str:
        if self._token_minter is not None:
            return self._token_minter(user)
        from app.infra.auth import create_access_token

        return create_access_token(user, lifetime_seconds=900)


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


def verify_host_token(*, host_token: str, verify_key: str, widget_id: UUID) -> dict[str, object]:
    try:
        header_segment, payload_segment, signature_segment = host_token.split(".")
        signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
        expected_signature = _b64url_encode(
            hmac.new(verify_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
        )
        if not hmac.compare_digest(signature_segment, expected_signature):
            raise ValueError("bad signature")
        header = _decode_json_segment(header_segment)
        payload = _decode_json_segment(payload_segment)
        if header.get("alg") != "HS256" or header.get("typ") != "JWT":
            raise ValueError("unsupported token")
        expires_at = int(payload["exp"])
        if expires_at <= int(datetime.now(UTC).timestamp()):
            raise ValueError("expired token")
        if str(payload.get("widget_id")) != str(widget_id):
            raise ValueError("wrong widget")
        if not payload.get("sub"):
            raise ValueError("missing subject")
        return payload
    except Exception as exc:  # noqa: BLE001 - hide token diagnostics from widget callers.
        raise UnauthorizedError(GENERIC_WIDGET_AUTH_ERROR) from exc


def sign_host_token(*, payload: dict[str, object], verify_key: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_segment = _b64url_json(header)
    payload_segment = _b64url_json(payload)
    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    signature = _b64url_encode(hmac.new(verify_key.encode("utf-8"), signing_input, hashlib.sha256).digest())
    return f"{header_segment}.{payload_segment}.{signature}"


def _decode_json_segment(segment: str) -> dict[str, object]:
    raw = base64.urlsafe_b64decode(_pad_b64(segment))
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("segment is not an object")
    return value


def _b64url_json(value: dict[str, object]) -> str:
    return _b64url_encode(json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _pad_b64(value: str) -> bytes:
    return (value + "=" * (-len(value) % 4)).encode("ascii")
