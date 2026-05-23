from __future__ import annotations

import asyncio
import logging
from threading import Lock

from core.config import Settings
from schemas.ocr import SourceLanguage
from utils.text_cleaner import clean_ocr_text, preview_ocr_text


logger = logging.getLogger(__name__)


class GoogleVisionOCRService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = None
        self._client_lock = Lock()

    async def extract(self, image_bytes: bytes | None, source_language: SourceLanguage) -> dict[str, object]:
        if not image_bytes:
            return {"engine": "google", "text": "", "confidence": 0.0}

        try:
            text, confidence = await asyncio.to_thread(self._extract_sync, image_bytes, source_language)
            return {"engine": "google", "text": text, "confidence": confidence}
        except Exception as exc:
            logger.warning("Google Vision OCR failed: %s", exc)
            return {"engine": "google", "text": "", "confidence": 0.0}

    def _extract_sync(self, image_bytes: bytes, source_language: SourceLanguage) -> tuple[str, float]:
        vision = self._get_vision_module()
        client = self._get_client(vision)
        image = vision.Image(content=image_bytes)
        context = vision.ImageContext(language_hints=self._language_hints(source_language))

        response = client.document_text_detection(
            image=image,
            image_context=context,
        )

        if response.error.message:
            raise RuntimeError(f"Google Vision API error: {response.error.message}")

        raw_text = response.full_text_annotation.text or ""
        full_text = clean_ocr_text(raw_text)
        logger.debug("Google Vision cleaned response preview: %s", preview_ocr_text(full_text))
        if not full_text:
            raise RuntimeError("Google Vision returned empty or corrupted text.")

        confidence = self._compute_confidence(response.full_text_annotation)
        logger.info("Google Vision OCR produced %s chars", len(full_text))
        return full_text, confidence

    def _get_vision_module(self):
        try:
            from google.cloud import vision  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"Google Vision SDK is unavailable: {exc}") from exc
        return vision

    def _get_client(self, vision_module):
        if self._client is not None:
            return self._client

        with self._client_lock:
            if self._client is None:
                self._client = vision_module.ImageAnnotatorClient()
                logger.info("Google Vision client initialised")
        return self._client

    def _language_hints(self, source_language: SourceLanguage) -> list[str]:
        hints = [source_language.value]
        for hint in self._settings.google_vision_language_hints_list:
            if hint not in hints:
                hints.append(hint)
        return hints

    def _compute_confidence(self, annotation) -> float:
        scores: list[float] = []
        for page in getattr(annotation, "pages", []) or []:
            for block in getattr(page, "blocks", []) or []:
                for paragraph in getattr(block, "paragraphs", []) or []:
                    for word in getattr(paragraph, "words", []) or []:
                        for symbol in getattr(word, "symbols", []) or []:
                            confidence = getattr(symbol, "confidence", 0.0) or 0.0
                            if confidence > 0:
                                scores.append(float(confidence))

        if not scores:
            return 0.85
        return round(sum(scores) / len(scores), 4)
