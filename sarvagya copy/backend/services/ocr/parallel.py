from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Awaitable

from core.config import Settings
from schemas.consensus import OCRCandidate, OCREnsembleResult
from schemas.ocr import SourceLanguage
from services.consensus import OCRConsensusEngine
from services.ocr.azure import AzureOCRService
from services.ocr.gemini import GeminiOCRService
from services.ocr.google import GoogleVisionOCRService
from services.ocr.sarvam import SarvamOCRService
from utils.file_handler import UploadPayload
from utils.text_cleaner import clean_ocr_text, preview_ocr_text


logger = logging.getLogger(__name__)


class ParallelOCRService:
    def __init__(
        self,
        sarvam_service: SarvamOCRService,
        google_service: GoogleVisionOCRService,
        azure_service: AzureOCRService,
        gemini_service: GeminiOCRService,
        consensus_engine: OCRConsensusEngine,
        settings: Settings,
    ) -> None:
        self._sarvam_service = sarvam_service
        self._google_service = google_service
        self._azure_service = azure_service
        self._gemini_service = gemini_service
        self._consensus_engine = consensus_engine
        self._settings = settings

    async def run(self, payload: UploadPayload, source_language: SourceLanguage) -> OCREnsembleResult:
        normalized_bytes, normalized_filename = await self._prepare_payload(payload)

        sarvam_task = self._run_engine(
            "sarvam",
            self._sarvam_service.extract_bytes(
                content=normalized_bytes or payload.content,
                filename=normalized_filename or payload.filename or "upload.png",
                source_language=source_language,
            )
            if normalized_bytes is not None
            else self._sarvam_service.extract(payload=payload, source_language=source_language),
        )

        google_task = self._run_engine(
            "google",
            self._google_service.extract(normalized_bytes, source_language),
        )
        azure_task = self._run_engine(
            "azure",
            self._azure_service.extract(normalized_bytes, source_language),
        )
        gemini_task = self._run_engine(
            "gemini",
            self._gemini_service.extract(normalized_bytes, source_language),
        )

        outputs = await asyncio.gather(sarvam_task, google_task, azure_task, gemini_task)
        consensus = self._consensus_engine.select(outputs)

        return OCREnsembleResult(
            outputs=[OCRCandidate(**output) for output in outputs],
            consensus=consensus,
        )

    async def _prepare_payload(self, payload: UploadPayload) -> tuple[bytes | None, str | None]:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._prepare_payload_sync, payload),
                timeout=self._settings.ocr_timeout_seconds,
            )
        except Exception as exc:
            logger.warning("OCR preprocessing failed, falling back to raw Sarvam only: %s", exc)
            return None, None

    def _prepare_payload_sync(self, payload: UploadPayload) -> tuple[bytes, str]:
        from services.ocr.preprocessor import pdf_to_image_bytes, preprocess

        filename = Path(payload.filename or "upload").name
        suffix = Path(filename).suffix.lower()
        stem = Path(filename).stem or "upload"

        if suffix == ".pdf":
            return pdf_to_image_bytes(payload.content), f"{stem}.png"

        return preprocess(payload.content), f"{stem}.png"

    async def _run_engine(self, engine: str, coroutine: Awaitable[dict[str, Any]]) -> dict[str, Any]:
        try:
            result = await asyncio.wait_for(coroutine, timeout=self._settings.ocr_timeout_seconds)
        except asyncio.TimeoutError:
            logger.warning("%s OCR timed out after %.1fs", engine, self._settings.ocr_timeout_seconds)
            return {"engine": engine, "text": "", "confidence": 0.0}
        except Exception as exc:
            logger.warning("%s OCR failed: %s", engine, exc)
            return {"engine": engine, "text": "", "confidence": 0.0}

        return self._coerce_result(engine, result)

    def _coerce_result(self, engine: str, result: Any) -> dict[str, Any]:
        if isinstance(result, OCRCandidate):
            return self._coerce_result(engine, result.model_dump())

        if not isinstance(result, dict):
            return {"engine": engine, "text": "", "confidence": 0.0}

        raw_text = str(result.get("text") or "")
        text = clean_ocr_text(raw_text)
        if raw_text and raw_text != text:
            logger.debug(
                "%s OCR output sanitized: raw=%s cleaned=%s",
                engine,
                preview_ocr_text(raw_text),
                preview_ocr_text(text),
            )
        confidence_value = result.get("confidence", 0.0)
        try:
            confidence = float(confidence_value or 0.0)
        except (TypeError, ValueError):
            confidence = 0.0

        return {
            "engine": str(result.get("engine") or engine),
            "text": text,
            "confidence": max(0.0, min(1.0, confidence)) if text else 0.0,
        }
