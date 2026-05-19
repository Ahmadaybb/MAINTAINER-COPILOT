from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.domain.errors import BootValidationError
from app.infra.artifact import ArtifactStore, assert_nonzero_thresholds


def create_app() -> FastAPI:
    app = FastAPI(title="Maintainer's Copilot Modelserver")
    app.state.ready = False
    app.state.artifact = None

    @app.on_event("startup")
    async def _startup() -> None:
        app.state.artifact = ArtifactStore().verify_and_load()
        assert_nonzero_thresholds()
        app.state.ready = True

    @app.exception_handler(BootValidationError)
    async def _boot_error_handler(_request, exc: BootValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz() -> JSONResponse | dict[str, str]:
        if not app.state.ready:
            return JSONResponse(
                status_code=503,
                content={"error": {"code": "boot_validation_error", "message": "Modelserver is not ready."}},
            )
        return {"status": "ready"}

    return app


app = create_app()
