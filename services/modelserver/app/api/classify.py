from __future__ import annotations

from fastapi import APIRouter, Request

from app.domain.classify import ClassifyRequest, ClassifyResponse

router = APIRouter(tags=["classification"])


@router.post("/classify", response_model=ClassifyResponse)
async def classify(payload: ClassifyRequest, request: Request) -> ClassifyResponse:
    return request.app.state.classifier.classify(payload.text)
