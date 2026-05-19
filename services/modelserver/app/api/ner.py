from __future__ import annotations

from fastapi import APIRouter, Request

from app.domain.ner import NerRequest, NerResponse

router = APIRouter(tags=["ner"])


@router.post("/ner", response_model=NerResponse)
async def ner(payload: NerRequest, request: Request) -> NerResponse:
    return request.app.state.ner.extract(payload.text)
