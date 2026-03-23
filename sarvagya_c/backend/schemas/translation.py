from __future__ import annotations

from pydantic import BaseModel, Field

from schemas.ocr import SourceLanguage


class TranslationRequest(BaseModel):
    text: str = Field(..., min_length=1)
    source_language: SourceLanguage = Field(default=SourceLanguage.SANSKRIT)
    target_language: str = Field(default="en-IN")


class TranslationResponse(BaseModel):
    source_text: str
    translated_text: str
    source_language: SourceLanguage
    target_language: str
    model: str
    raw_response: dict = Field(default_factory=dict)
