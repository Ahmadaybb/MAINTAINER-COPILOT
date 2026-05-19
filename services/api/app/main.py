from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.admin_invitations import router as admin_invitations_router
from app.api.deps import RequestIdMiddleware
from app.api.auth import router as auth_router
from app.api.triage import router as triage_router
from app.domain.errors import (
    BootValidationError,
    DomainError,
    ToolFailure,
    UpstreamUnavailable,
    ValidationError,
)
from app.infra.logging import configure_logging, current_request_id, current_trace_id
from app.infra.modelserver_client import ModelserverClient
from app.infra.tracing import configure_tracing
from app.infra.vault import get_app_secrets

logger = logging.getLogger(__name__)

THRESHOLDS_PATH = Path(__file__).resolve().parents[3] / "eval_thresholds.yaml"

STATUS_BY_CODE = {
    "not_found": 404,
    "permission_denied": 403,
    "rate_limited": 429,
    "tool_failure": 502,
    "validation_error": 400,
    "upstream_unavailable": 503,
    "gone": 410,
    "boot_validation_error": 503,
}


def _error_envelope(error: DomainError, request: Request | None = None) -> dict[str, Any]:
    request_id = getattr(request.state, "request_id", current_request_id()) if request else current_request_id()
    return {
        "error": {
            "code": error.code,
            "message": error.message,
            "request_id": request_id,
            "trace_id": current_trace_id(),
        }
    }


def assert_nonzero_thresholds(path: Path = THRESHOLDS_PATH) -> Mapping[str, Any]:
    if not path.exists():
        raise BootValidationError("Eval thresholds are required at startup.")
    thresholds = _parse_simple_yaml(path.read_text(encoding="utf-8"))
    required = (
        ("classification", "macro_f1"),
        ("rag", "context_recall"),
        ("rag", "faithfulness"),
        ("rag", "answer_relevancy"),
    )
    for section, key in required:
        value = thresholds.get(section, {}).get(key)
        if not isinstance(value, (int, float)) or value <= 0:
            raise BootValidationError("Eval thresholds must be non-zero.")
    return thresholds


def _parse_simple_yaml(raw: str) -> dict[str, dict[str, float]]:
    parsed: dict[str, dict[str, float]] = {}
    section: str | None = None
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith(" ") and line.endswith(":"):
            section = line[:-1].strip()
            parsed[section] = {}
            continue
        if section and ":" in line:
            key, value = line.split(":", 1)
            parsed[section][key.strip()] = float(value.strip())
    return parsed


async def run_boot_checks(app: FastAPI) -> None:
    get_app_secrets()
    assert_nonzero_thresholds()
    modelserver_ready = await ModelserverClient().ready()
    if not modelserver_ready:
        raise BootValidationError("Modelserver readiness check failed.")
    app.state.ready = True


def create_app(run_startup_checks: bool = True) -> FastAPI:
    configure_logging()
    configure_tracing()

    app = FastAPI(title="Maintainer's Copilot API")
    app.state.ready = False
    app.add_middleware(RequestIdMiddleware)
    app.include_router(auth_router)
    app.include_router(admin_invitations_router)
    app.include_router(triage_router)

    @app.on_event("startup")
    async def _startup() -> None:
        if run_startup_checks:
            await run_boot_checks(app)
        else:
            app.state.ready = True

    @app.exception_handler(DomainError)
    async def _domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=STATUS_BY_CODE.get(exc.code, 500),
            content=_error_envelope(exc, request),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(request: Request, _exc: RequestValidationError) -> JSONResponse:
        error = ValidationError("The request is invalid.")
        return JSONResponse(status_code=422, content=_error_envelope(error, request))

    @app.exception_handler(Exception)
    async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception", exc_info=exc)
        error = ToolFailure("An unexpected error occurred. Please try again shortly.")
        return JSONResponse(status_code=500, content=_error_envelope(error, request))

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz() -> JSONResponse | dict[str, str]:
        if not app.state.ready:
            error = UpstreamUnavailable("The API is not ready.")
            return JSONResponse(status_code=503, content=_error_envelope(error))
        return {"status": "ready"}

    return app


app = create_app()
