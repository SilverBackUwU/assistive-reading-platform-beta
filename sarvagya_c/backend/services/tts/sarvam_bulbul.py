from __future__ import annotations

from core.config import Settings
from core.exceptions import ExternalServiceError
from schemas.tts import TTSRequest, TTSResponse
from services.shared.sarvam_client import SarvamClient


class SarvamTTSService:
    def __init__(self, client: SarvamClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    async def synthesize(self, request: TTSRequest) -> TTSResponse:
        voice = request.voice or self._settings.sarvam_tts_voice
        response = await self._client.post_json(
            endpoint=self._settings.sarvam_tts_endpoint,
            payload={
                "model": self._settings.sarvam_tts_model,
                "text": request.text,
                "speaker": voice,
                "target_language_code": request.language_code,
            },
        )

        audio_base64 = (
            response.get("audio_base64")
            or response.get("audio")
            or response.get("output", {}).get("audio_base64")
            or _first_audio(response.get("audios"))
        )
        if not audio_base64:
            raise ExternalServiceError(
                "Sarvam Bulbul response did not include audio data.",
                code="SARVAM_TTS_EMPTY_AUDIO",
            )

        return TTSResponse(
            text=request.text,
            voice=voice,
            model=str(response.get("model") or self._settings.sarvam_tts_model),
            mime_type=str(response.get("mime_type") or "audio/wav"),
            audio_base64=audio_base64,
            raw_response=response,
        )


def _first_audio(value: object) -> str | None:
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, str):
            return first
    return None
