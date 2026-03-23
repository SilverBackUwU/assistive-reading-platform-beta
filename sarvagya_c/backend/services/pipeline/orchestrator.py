from __future__ import annotations

from uuid import uuid4

from core.exceptions import AppError
from repositories.job_store import InMemoryJobRepository
from schemas.braille import BrailleRequest
from schemas.ocr import SourceLanguage
from schemas.pipeline import PipelineResponse, PipelineStatus
from schemas.translation import TranslationRequest
from schemas.tts import TTSRequest
from services.braille.liblouis_service import LiblouisBrailleService
from services.ocr.sarvam_vision import SarvamOCRService
from services.translation.sarvam_translate import SarvamTranslationService
from services.tts.sarvam_bulbul import SarvamTTSService
from utils.file_handler import UploadPayload


class PipelineService:
    def __init__(
        self,
        job_repository: InMemoryJobRepository,
        ocr_service: SarvamOCRService,
        translation_service: SarvamTranslationService,
        braille_service: LiblouisBrailleService,
        tts_service: SarvamTTSService,
    ) -> None:
        self._job_repository = job_repository
        self._ocr_service = ocr_service
        self._translation_service = translation_service
        self._braille_service = braille_service
        self._tts_service = tts_service

    async def run(self, payload: UploadPayload, source_language: SourceLanguage) -> PipelineResponse:
        job_id = str(uuid4())
        try:
            ocr_result = await self._ocr_service.extract_text(payload=payload, source_language=source_language)
            translation_result = await self._translation_service.translate_text(
                TranslationRequest(text=ocr_result.extracted_text, source_language=source_language)
            )
            braille_result = await self._braille_service.transcribe(
                BrailleRequest(text=translation_result.translated_text)
            )
            tts_result = await self._tts_service.synthesize(
                TTSRequest(text=translation_result.translated_text)
            )

            result = PipelineResponse(
                job_id=job_id,
                status=PipelineStatus.COMPLETED,
                source_language=source_language,
                ocr=ocr_result,
                translation=translation_result,
                braille=braille_result,
                tts=tts_result,
            )
        except AppError as exc:
            result = PipelineResponse(
                job_id=job_id,
                status=PipelineStatus.FAILED,
                source_language=source_language,
                error=exc.message,
            )

        self._job_repository.save(result)
        return result

    def get_job(self, job_id: str) -> PipelineResponse:
        return self._job_repository.get(job_id)
