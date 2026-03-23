from __future__ import annotations

from core.config import Settings
from core.exceptions import ExternalServiceError
from schemas.translation import TranslationRequest, TranslationResponse
from services.shared.sarvam_client import SarvamClient


class SarvamTranslationService:
    def __init__(self, client: SarvamClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    async def translate_text(self, request: TranslationRequest) -> TranslationResponse:
        response = await self._client.post_json(
            endpoint=self._settings.sarvam_translate_endpoint,
            payload={
                "model": self._settings.sarvam_translate_model,
                "input": request.text,
                "source_language_code": f"{request.source_language.value}-IN",
                "target_language_code": request.target_language,
            },
        )

        translated_text = (
            response.get("translated_text")
            or response.get("translation")
            or response.get("output", {}).get("text")
        )
        if not translated_text:
            raise ExternalServiceError(
                "Sarvam Translate response did not include translated text.",
                code="SARVAM_TRANSLATE_EMPTY_TEXT",
            )

        return TranslationResponse(
            source_text=request.text,
            translated_text=translated_text,
            source_language=request.source_language,
            target_language=request.target_language,
            model=str(response.get("model") or self._settings.sarvam_translate_model),
            raw_response=response,
        )
