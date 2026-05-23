from __future__ import annotations

import asyncio
import logging
from threading import Lock

from core.config import Settings
from schemas.ocr import SourceLanguage
from utils.text_cleaner import clean_ocr_text, preview_ocr_text


logger = logging.getLogger(__name__)


class AzureOCRService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = None
        self._client_lock = Lock()

    async def extract(self, image_bytes: bytes | None, source_language: SourceLanguage) -> dict[str, object]:
        if not image_bytes:
            return {"engine": "azure", "text": "", "confidence": 0.0}

        try:
            text, confidence = await asyncio.to_thread(self._extract_sync, image_bytes, source_language)
            return {"engine": "azure", "text": text, "confidence": confidence}
        except Exception as exc:
            logger.warning("Azure OCR failed: %s", exc)
            return {"engine": "azure", "text": "", "confidence": 0.0}

    def _extract_sync(self, image_bytes: bytes, source_language: SourceLanguage) -> tuple[str, float]:
        client = self._get_client()

        try:
            from azure.ai.documentintelligence.models import AnalyzeDocumentRequest  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"Azure Document Intelligence SDK is unavailable: {exc}") from exc

        locale = self._locale_for(source_language)
        poller = client.begin_analyze_document(
            model_id=self._model_id(),
            analyze_request=AnalyzeDocumentRequest(bytes_source=image_bytes),
            locale=locale,
            content_type="application/octet-stream",
        )
        result = poller.result()

        if not result or not getattr(result, "content", None):
            raise RuntimeError("Azure returned empty content.")

        raw_text = str(result.content or "")
        full_text = clean_ocr_text(raw_text)
        logger.debug("Azure OCR cleaned response preview: %s", preview_ocr_text(full_text))
        if not full_text:
            raise RuntimeError("Azure returned empty or corrupted text.")

        confidence = self._compute_confidence(result)
        logger.info("Azure OCR produced %s chars", len(full_text))
        return full_text, confidence

    def _get_client(self):
        if self._client is not None:
            return self._client

        with self._client_lock:
            if self._client is not None:
                return self._client

            if not self._settings.azure_doc_intel_endpoint or not self._settings.azure_doc_intel_key:
                raise RuntimeError("Azure Document Intelligence settings are missing.")

            try:
                from azure.ai.documentintelligence import DocumentIntelligenceClient  # type: ignore
                from azure.core.credentials import AzureKeyCredential  # type: ignore
            except Exception as exc:  # pragma: no cover
                raise RuntimeError(f"Azure SDK is unavailable: {exc}") from exc

            self._client = DocumentIntelligenceClient(
                endpoint=self._settings.azure_doc_intel_endpoint,
                credential=AzureKeyCredential(self._settings.azure_doc_intel_key),
            )
            logger.info("Azure Document Intelligence client initialised")
            return self._client

    def _model_id(self) -> str:
        return self._settings.azure_doc_intel_model_id or "prebuilt-read"

    def _locale_for(self, source_language: SourceLanguage) -> str:
        if source_language == SourceLanguage.HINDI:
            return "hi"
        return self._settings.azure_doc_intel_language or "sa"

    def _compute_confidence(self, result) -> float:
        scores: list[float] = []
        try:
            for page in getattr(result, "pages", []) or []:
                for word in getattr(page, "words", []) or []:
                    confidence = getattr(word, "confidence", None)
                    if confidence is not None:
                        scores.append(float(confidence))
        except Exception:
            pass

        if not scores:
            return 0.87
        return round(sum(scores) / len(scores), 4)
