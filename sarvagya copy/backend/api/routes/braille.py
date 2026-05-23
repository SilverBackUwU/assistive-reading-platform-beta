from __future__ import annotations

from fastapi import APIRouter

from api.deps import BrailleServiceDep
from schemas.braille import BrailleRequest, BrailleResponse


router = APIRouter(prefix="/braille", tags=["Braille"])


@router.post("/transcribe", response_model=BrailleResponse, summary="English to Grade 2 Braille")
async def transcribe_braille(
    request: BrailleRequest,
    service: BrailleServiceDep,
) -> BrailleResponse:
    return await service.transcribe(request)
