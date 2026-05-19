from __future__ import annotations

import os
from typing import Any

import httpx


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1").rstrip("/")


class ApiError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def request(
    method: str,
    path: str,
    *,
    token: str | None = None,
    json: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> Any:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        with httpx.Client(timeout=20) as client:
            response = client.request(
                method,
                f"{API_BASE_URL}{path}",
                headers=headers,
                json=json,
                params=params,
            )
    except httpx.HTTPError as exc:
        raise ApiError("API is unavailable.") from exc
    if response.status_code >= 400:
        raise ApiError(_error_message(response), response.status_code)
    if response.content:
        return response.json()
    return None


def login(email: str, password: str) -> str:
    payload = request("POST", "/auth/jwt/login", json={"email": email, "password": password})
    return str(payload["access_token"])


def _error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return "Request failed."
    error = payload.get("error", {})
    return str(error.get("message") or "Request failed.")
