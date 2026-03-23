from __future__ import annotations

from fastapi import APIRouter

from api.deps import TTSServiceDep
from schemas.tts import TTSRequest, TTSResponse


router = APIRouter(prefix="/tts", tags=["TTS"])


@router.post("/synthesize", response_model=TTSResponse, summary="Read-aloud via Sarvam Bulbul")
async def synthesize_audio(
    request: TTSRequest,
    service: TTSServiceDep,
) -> TTSResponse:
    return await service.synthesize(request)
