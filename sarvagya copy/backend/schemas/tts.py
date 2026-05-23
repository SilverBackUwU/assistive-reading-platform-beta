from __future__ import annotations

from pydantic import BaseModel, Field


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1)
    voice: str | None = Field(default=None)
    language_code: str = Field(default="en-IN")


class TTSResponse(BaseModel):
    text: str
    voice: str
    model: str
    mime_type: str
    audio_base64: str
    raw_response: dict = Field(default_factory=dict)
