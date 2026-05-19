from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.classify import router as classify_router
from app.api.ner import router as ner_router
from app.domain.errors import BootValidationError
from app.infra.artifact import ArtifactStore, assert_nonzero_thresholds
from app.services.classifier import ClassifierService
from app.services.ner import NerService


def create_app() -> FastAPI:
    app = FastAPI(title="Maintainer's Copilot Modelserver")
    app.state.ready = False
    app.state.artifact = None
    app.include_router(classify_router)
    app.include_router(ner_router)

    @app.on_event("startup")
    async def _startup() -> None:
        app.state.artifact = ArtifactStore().verify_and_load()
        assert_nonzero_thresholds()
        app.state.classifier = ClassifierService(app.state.artifact)
        app.state.ner = NerService()
        app.state.ready = True

    @app.exception_handler(BootValidationError)
    async def _boot_error_handler(_request: Request, exc: BootValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(_request: Request, _exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "validation_error", "message": "The request is invalid."}},
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
