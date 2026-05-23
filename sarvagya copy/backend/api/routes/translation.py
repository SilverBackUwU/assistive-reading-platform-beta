from __future__ import annotations

from fastapi import APIRouter

from api.deps import TranslationServiceDep
from schemas.translation import TranslationRequest, TranslationResponse


router = APIRouter(prefix="/translate", tags=["Translation"])


@router.post("/text", response_model=TranslationResponse, summary="Translate to English")
async def translate_text(
    request: TranslationRequest,
    service: TranslationServiceDep,
) -> TranslationResponse:
    return await service.translate_text(request)
