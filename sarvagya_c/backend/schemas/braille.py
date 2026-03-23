from __future__ import annotations

from pydantic import BaseModel, Field


class BrailleRequest(BaseModel):
    text: str = Field(..., min_length=1, description="English text to transcribe.")
    table: str | None = Field(default=None, description="Override Liblouis translation table.")


class BrailleResponse(BaseModel):
    source_text: str
    braille_unicode: str
    brf_text: str
    table: str
    engine: str = Field(default="liblouis")
