from __future__ import annotations

import logging
from uuid import uuid4

from core.exceptions import AppError
from repositories.job_store import InMemoryJobRepository
from schemas.consensus import OCREnsembleResult
from schemas.braille import BrailleRequest
from schemas.ocr import SourceLanguage
from schemas.pipeline import PipelineResponse, PipelineStatus
from schemas.translation import TranslationRequest
from schemas.tts import TTSRequest
from services.braille.liblouis_service import LiblouisBrailleService
from services.ocr.parallel import ParallelOCRService
from services.translation.sarvam_translate import SarvamTranslationService
from services.tts.sarvam_bulbul import SarvamTTSService
from utils.file_handler import UploadPayload


logger = logging.getLogger(__name__)


class PipelineService:
    def __init__(
        self,
        job_repository: InMemoryJobRepository,
        ocr_service: ParallelOCRService,
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
        ensemble: OCREnsembleResult | None = None

        try:
            ensemble = await self._ocr_service.run(payload=payload, source_language=source_language)

            if ensemble.consensus is None or not ensemble.consensus.text.strip():
                result = PipelineResponse(
                    job_id=job_id,
                    status=PipelineStatus.FAILED,
                    source_language=source_language,
                    ocr_outputs=ensemble.outputs,
                    error="All OCR engines failed or returned empty text.",
                )
                self._job_repository.save(result)
                return result

            translation_result = await self._translation_service.translate_text(
                TranslationRequest(text=ensemble.consensus.text, source_language=source_language)
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
                ocr=ensemble.consensus,
                ocr_outputs=ensemble.outputs,
                translation=translation_result,
                braille=braille_result,
                tts=tts_result,
            )
        except AppError as exc:
            result = PipelineResponse(
                job_id=job_id,
                status=PipelineStatus.FAILED,
                source_language=source_language,
                ocr=ensemble.consensus if ensemble else None,
                ocr_outputs=ensemble.outputs if ensemble else [],
                error=exc.message,
            )
        except Exception as exc:
            logger.exception("Pipeline failed unexpectedly: %s", exc)
            result = PipelineResponse(
                job_id=job_id,
                status=PipelineStatus.FAILED,
                source_language=source_language,
                ocr=ensemble.consensus if ensemble else None,
                ocr_outputs=ensemble.outputs if ensemble else [],
                error=str(exc),
            )

        self._job_repository.save(result)
        return result

    def get_job(self, job_id: str) -> PipelineResponse:
        return self._job_repository.get(job_id)
