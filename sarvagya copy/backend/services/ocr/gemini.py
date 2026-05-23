from __future__ import annotations
from utils.text_cleaner import (
    clean_ocr_text,
    contains_encoded_image_payload,
    contains_giant_encoded_string,
    preview_ocr_text,
)

import asyncio
import base64
import logging
from threading import Lock

from core.config import Settings
from schemas.ocr import SourceLanguage


logger = logging.getLogger(__name__)


class GeminiOCRService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = None
        self._client_lock = Lock()

    async def extract(self, image_bytes: bytes | None, source_language: SourceLanguage) -> dict[str, object]:
        if not image_bytes:
            return {"engine": "gemini", "text": "", "confidence": 0.0}

        try:
            text, confidence = await asyncio.to_thread(self._extract_sync, image_bytes, source_language)
            return {"engine": "gemini", "text": text, "confidence": confidence}
        except Exception as exc:
            logger.warning("Gemini OCR failed: %s", exc)
            return {"engine": "gemini", "text": "", "confidence": 0.0}

    def _extract_sync(self, image_bytes: bytes, source_language: SourceLanguage) -> tuple[str, float]:
        client = self._get_client()
        image_part = {
            "mime_type": "image/png",
            "data": base64.b64encode(image_bytes).decode("utf-8"),
        }
        response = client.generate_content(
            [self._prompt_for(source_language), image_part])

        raw_text = response.text or ""
        logger.debug("Gemini raw response preview: %s", preview_ocr_text(raw_text))
        text = clean_ocr_text(raw_text)
        logger.debug("Gemini cleaned response preview: %s", preview_ocr_text(text))

        if contains_encoded_image_payload(raw_text) or contains_giant_encoded_string(raw_text):
            raise RuntimeError("Gemini returned encoded image data instead of OCR text.")

        if not text:
            raise RuntimeError("Gemini returned empty or corrupted text.")

        logger.info("Gemini OCR produced %s chars", len(text))
        return text, 0.84

    def _get_client(self):
        if self._client is not None:
            return self._client

        with self._client_lock:
            if self._client is not None:
                return self._client

            if not self._settings.gemini_api_key:
                raise RuntimeError(
                    "GEMINI_API_KEY is missing. Add it to your .env file.")

            try:
                import google.generativeai as genai  # type: ignore
            except Exception as exc:  # pragma: no cover
                raise RuntimeError(
                    f"Gemini SDK is unavailable: {exc}") from exc

            genai.configure(api_key=self._settings.gemini_api_key)
            self._client = genai.GenerativeModel(
                model_name=self._settings.gemini_model,
                generation_config={
                    "max_output_tokens": self._settings.gemini_max_output_tokens,
                    "temperature": 0.0,
                },
            )
            logger.info("Gemini client initialised: %s",
                        self._settings.gemini_model)
            return self._client

    def _prompt_for(self, source_language: SourceLanguage) -> str:
        language = "Hindi" if source_language == SourceLanguage.HINDI else "Sanskrit"
        return (
            f"You are an expert {language} OCR system.\n"
            "Extract all visible text exactly as it appears.\n"
            "Do not translate, paraphrase, or explain.\n"
            "Return ONLY plain extracted text.\n"
            "Do NOT return markdown.\n"
            "Do NOT return image data.\n"
            "Do NOT return base64.\n"
            "Do NOT describe the image.\n"
        )
