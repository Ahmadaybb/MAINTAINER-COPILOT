from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.api.deps import require_user
from app.domain.errors import UpstreamUnavailable, ValidationError
from app.infra.logging import current_trace_id
from app.domain.triage import TriageRequest, TriageResponse
from app.domain.user import AuthenticatedUser
from app.services.rate_limit import RateLimiter
from app.services.triage_service import TriageService

router = APIRouter(prefix="/api/v1", tags=["triage"])


def get_triage_service() -> TriageService:
    return TriageService()


def get_rate_limiter() -> RateLimiter:
    return RateLimiter()


@router.post("/triage", response_model=TriageResponse)
async def triage(
    payload: TriageRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_user)],
    triage_service: Annotated[TriageService, Depends(get_triage_service)],
    rate_limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> TriageResponse | JSONResponse:
    if bool(payload.issue_url) == bool(payload.issue_text):
        raise ValidationError("Provide exactly one of issue_url or issue_text.")

    rate_limiter.check(user.id)
    try:
        return await triage_service.triage(payload, request_id=request.state.request_id)
    except UpstreamUnavailable as exc:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": request.state.request_id,
                    "trace_id": current_trace_id(),
                }
            },
        )
