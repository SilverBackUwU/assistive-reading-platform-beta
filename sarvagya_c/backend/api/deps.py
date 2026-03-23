from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from core.config import get_settings
from repositories.job_store import InMemoryJobRepository
from services.braille.liblouis_service import LiblouisBrailleService
from services.ocr.sarvam_vision import SarvamOCRService
from services.pipeline.orchestrator import PipelineService
from services.shared.sarvam_client import SarvamClient
from services.translation.sarvam_translate import SarvamTranslationService
from services.tts.sarvam_bulbul import SarvamTTSService


settings = get_settings()
sarvam_client = SarvamClient(settings=settings)
job_repository = InMemoryJobRepository()
ocr_service = SarvamOCRService(client=sarvam_client, settings=settings)
translation_service = SarvamTranslationService(client=sarvam_client, settings=settings)
braille_service = LiblouisBrailleService(settings=settings)
tts_service = SarvamTTSService(client=sarvam_client, settings=settings)
pipeline_service = PipelineService(
    job_repository=job_repository,
    ocr_service=ocr_service,
    translation_service=translation_service,
    braille_service=braille_service,
    tts_service=tts_service,
)


def get_ocr_service() -> SarvamOCRService:
    return ocr_service


def get_translation_service() -> SarvamTranslationService:
    return translation_service


def get_braille_service() -> LiblouisBrailleService:
    return braille_service


def get_tts_service() -> SarvamTTSService:
    return tts_service


def get_pipeline_service() -> PipelineService:
    return pipeline_service


OCRServiceDep = Annotated[SarvamOCRService, Depends(get_ocr_service)]
TranslationServiceDep = Annotated[SarvamTranslationService, Depends(get_translation_service)]
BrailleServiceDep = Annotated[LiblouisBrailleService, Depends(get_braille_service)]
TTSServiceDep = Annotated[SarvamTTSService, Depends(get_tts_service)]
PipelineServiceDep = Annotated[PipelineService, Depends(get_pipeline_service)]
