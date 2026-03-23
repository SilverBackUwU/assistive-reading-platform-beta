from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from schemas.braille import BrailleResponse
from schemas.ocr import OCRResponse, SourceLanguage
from schemas.translation import TranslationResponse
from schemas.tts import TTSResponse


class PipelineStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineResponse(BaseModel):
    job_id: str
    status: PipelineStatus
    source_language: SourceLanguage
    ocr: OCRResponse | None = None
    translation: TranslationResponse | None = None
    braille: BrailleResponse | None = None
    tts: TTSResponse | None = None
    error: str | None = Field(default=None)
