from __future__ import annotations

from fastapi import APIRouter

from core.config import get_settings


router = APIRouter(tags=["System"])
settings = get_settings()


@router.get("/health", summary="Liveness check")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
    }


@router.get("/api/v1/endpoints", summary="List supported API endpoints")
async def endpoints() -> dict[str, list[dict[str, str]]]:
    return {
        "endpoints": [
            {"method": "GET", "path": "/health", "purpose": "Confirm the API is running."},
            {"method": "GET", "path": "/api/v1/endpoints", "purpose": "List the working endpoints in this backend."},
            {"method": "POST", "path": "/api/v1/ocr/extract", "purpose": "Upload an image or PDF and extract source text with Sarvam Vision."},
            {"method": "POST", "path": "/api/v1/translate/text", "purpose": "Translate extracted Hindi or Sanskrit text to English."},
            {"method": "POST", "path": "/api/v1/braille/transcribe", "purpose": "Convert English text into Grade 2 Braille and BRF-ready output."},
            {"method": "POST", "path": "/api/v1/tts/synthesize", "purpose": "Generate read-aloud audio with Sarvam Bulbul."},
            {"method": "POST", "path": "/api/v1/pipeline/run", "purpose": "Run the full upload through the OCR ensemble, translation, Braille, and TTS workflow."},
            {"method": "GET", "path": "/api/v1/pipeline/jobs/{job_id}", "purpose": "Fetch a saved pipeline result."},
        ]
    }
