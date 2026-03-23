"""
services/ocr/google_vision.py
==============================
Layer 1 — Google Cloud Vision OCR.
Package: google-cloud-vision==3.8.1

Auth: GOOGLE_APPLICATION_CREDENTIALS points to a service account JSON file.
      Set this in .env:
        GOOGLE_APPLICATION_CREDENTIALS=./credentials/google_vision.json

How to get the credentials file:
  1. Go to console.cloud.google.com
  2. IAM & Admin → Service Accounts → Create
  3. Grant role: Cloud Vision API User
  4. Keys → Add Key → JSON → download
  5. Save as backend/credentials/google_vision.json
  6. Enable Cloud Vision API in your project
"""
from __future__ import annotations

import logging
import os

from schemas.ocr import LayerOutput, OCREngineLabel
from services.ocr.base import OCREngine

logger = logging.getLogger(__name__)


class GoogleVisionOCR(OCREngine):
    """
    Calls Google Cloud Vision TEXT_DETECTION on preprocessed image bytes.
    Returns full document text with a confidence score.
    """

    def __init__(self, language_hints: list[str]):
        """
        Args:
            language_hints: e.g. ["sa", "hi"] — Sanskrit first, Hindi fallback
        """
        self._language_hints = language_hints
        self._client = None  # lazy init — don't crash on import if key missing

    @property
    def engine_name(self) -> str:
        return OCREngineLabel.GOOGLE

    def _get_client(self):
        """Lazy-initialise Vision client. Fails loudly if credentials missing."""
        if self._client is None:
            try:
                from google.cloud import vision
                self._client = vision.ImageAnnotatorClient()
                logger.info("Google Vision client initialised")
            except Exception as e:
                raise RuntimeError(
                    f"Google Vision client failed to initialise: {e}\n"
                    f"Check GOOGLE_APPLICATION_CREDENTIALS in .env points to "
                    f"a valid service account JSON file."
                ) from e
        return self._client

    async def extract(self, image_bytes: bytes) -> LayerOutput:
        try:
            from google.cloud import vision

            client = self._get_client()

            image = vision.Image(content=image_bytes)
            context = vision.ImageContext(language_hints=self._language_hints)

            response = client.document_text_detection(
                image=image,
                image_context=context,
            )

            # Hard fail on API-level errors
            if response.error.message:
                raise RuntimeError(
                    f"Google Vision API error: {response.error.message}"
                )

            full_text = response.full_text_annotation.text.strip()

            if not full_text:
                return LayerOutput(
                    engine=OCREngineLabel.GOOGLE,
                    text="",
                    confidence=0.0,
                    success=False,
                    error="Google Vision returned empty text",
                )

            # Average confidence across all detected symbols
            confidence = _compute_google_confidence(
                response.full_text_annotation)

            logger.info(
                f"Google Vision: {len(full_text)} chars, "
                f"confidence={confidence:.3f}"
            )
            return LayerOutput(
                engine=OCREngineLabel.GOOGLE,
                text=full_text,
                confidence=confidence,
                success=True,
            )

        except Exception as e:
            logger.error(f"Google Vision failed: {e}")
            return LayerOutput(
                engine=OCREngineLabel.GOOGLE,
                text="",
                confidence=0.0,
                success=False,
                error=str(e),
            )


def _compute_google_confidence(annotation) -> float:
    """
    Average confidence across every Symbol in the full text annotation.
    Google Vision exposes confidence per symbol — we aggregate to a document score.
    """
    scores = []
    for page in annotation.pages:
        for block in page.blocks:
            for paragraph in block.paragraphs:
                for word in paragraph.words:
                    for symbol in word.symbols:
                        if symbol.confidence > 0:
                            scores.append(symbol.confidence)
    if not scores:
        return 0.85  # Google Vision often omits confidence — use reasonable default
    return round(sum(scores) / len(scores), 4)
