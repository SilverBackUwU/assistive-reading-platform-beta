from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class SourceLanguage(str, Enum):
    HINDI = "hi"
    SANSKRIT = "sa"


class OCRResponse(BaseModel):
    source_language: SourceLanguage
    extracted_text: str = Field(..., description="Text returned by Sarvam Vision.")
    model: str = Field(..., description="Vision model used for OCR.")
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    page_count: int | None = Field(default=None, ge=1)
    raw_response: dict = Field(default_factory=dict)
