from __future__ import annotations

import uuid
from typing import Annotated
from collections.abc import Awaitable, Callable

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi_users.jwt import decode_jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.domain.errors import PermissionDenied
from app.domain.user import AuthenticatedUser, UserRole
from app.infra.auth import user_from_token_payload
from app.infra.logging import request_id_var
from app.infra.vault import get_app_secrets

bearer_scheme = HTTPBearer(auto_error=False)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        token = request_id_var.set(request_id)
        request.state.request_id = request_id
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["x-request-id"] = request_id
        return response


async def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> AuthenticatedUser:
    if credentials is None:
        raise PermissionDenied("Authentication is required.")
    try:
        payload = decode_jwt(
            credentials.credentials,
            get_app_secrets().jwt_signing_key,
            audience=["fastapi-users:auth"],
        )
        user = user_from_token_payload(payload)
    except Exception as exc:  # noqa: BLE001 - auth dependency maps to domain error.
        raise PermissionDenied("Authentication is required.") from exc
    if not user.is_active:
        raise PermissionDenied("Authentication is required.")
    return user


async def require_user(user: Annotated[AuthenticatedUser, Depends(current_user)]) -> AuthenticatedUser:
    return user


async def require_admin(
    user: Annotated[AuthenticatedUser, Depends(current_user)],
) -> AuthenticatedUser:
    if user.role != UserRole.ADMIN:
        raise PermissionDenied("Administrator access is required.")
    return user
