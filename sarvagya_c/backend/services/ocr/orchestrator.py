"""
services/ocr/orchestrator.py
=============================
Runs Layer 1, 2, 3 in parallel using asyncio.gather.
If ANY engine fails → raises OCRPipelineError immediately (per your requirement).
After parallel run → consensus engine merges → Gemini arbitrates conflicts.

This is the single entry point called by the route handler.
"""
from __future__ import annotations

import asyncio
import logging
import time

from core.config import get_settings
from schemas.ocr import LayerOutput, OCREngineLabel, OCRResponse, WordResult
from services.ocr import consensus as consensus_engine
from services.ocr.azure_ocr import AzureDocumentOCR
from services.ocr.gemini_ocr import GeminiOCR
from services.ocr.google_vision import GoogleVisionOCR
from utils.id_generator import make_job_id

logger = logging.getLogger(__name__)


class OCRPipelineError(Exception):
    """
    Raised when any OCR engine fails.
    Carries which engine failed and why.
    """

    def __init__(self, engine: str, reason: str):
        self.engine = engine
        self.reason = reason
        super().__init__(f"{engine} failed: {reason}")


class OCROrchestrator:
    """
    Singleton-safe orchestrator. Instantiated once at app startup via deps.py.
    Reuses the same SDK clients across requests (no re-auth overhead).
    """

    def __init__(self):
        cfg = get_settings()

        self._google = GoogleVisionOCR(
            language_hints=cfg.google_language_hints_list,
        )
        self._azure = AzureDocumentOCR(
            endpoint=cfg.azure_doc_intel_endpoint,
            key=cfg.azure_doc_intel_key,
            model_id=cfg.azure_ocr_model_id,
            language=cfg.azure_ocr_language,
        )
        self._gemini = GeminiOCR(
            api_key=cfg.gemini_api_key,
            model=cfg.gemini_model,
            max_tokens=cfg.gemini_ocr_max_tokens,
        )

        logger.info("OCROrchestrator initialised (Google + Azure + Gemini)")

    async def run(
        self,
        image_bytes: bytes,
        source_language: str = "sa",
    ) -> OCRResponse:
        """
        Full pipeline: parallel OCR → consensus → arbitration → response.

        Args:
            image_bytes:     preprocessed PNG bytes from preprocessor.py
            source_language: "sa" (Sanskrit) or "hi" (Hindi)

        Returns:
            OCRResponse with merged_text + word_results + layer_outputs

        Raises:
            OCRPipelineError if any engine fails (hard-fail policy)
        """
        start_ms = int(time.time() * 1000)
        job_id = make_job_id()

        logger.info(f"[{job_id}] Starting OCR pipeline ({source_language})")

        # ── Step 1: Run all 3 engines in parallel ─────────────────────────
        google_result, azure_result, gemini_result = await asyncio.gather(
            self._google.extract(image_bytes),
            self._azure.extract(image_bytes),
            self._gemini.extract(image_bytes),
            return_exceptions=False,  # let real exceptions propagate
        )

        layer_outputs = [google_result, azure_result, gemini_result]

        # ── Step 2: Hard-fail if ANY engine failed ─────────────────────────
        # Per your requirement: "Fail the whole request — need all 3"
        for output in layer_outputs:
            if not output.success:
                logger.error(
                    f"[{job_id}] Engine {output.engine} failed: {output.error}"
                )
                raise OCRPipelineError(
                    engine=output.engine.value,
                    reason=output.error or "Unknown error",
                )

        logger.info(
            f"[{job_id}] All 3 engines succeeded — "
            f"G:{len(google_result.text)}c "
            f"A:{len(azure_result.text)}c "
            f"M:{len(gemini_result.text)}c"
        )

        # ── Step 3: First-pass consensus (no arbiter yet) ─────────────────
        merged_text, word_results = consensus_engine.merge(
            google=google_result,
            azure=azure_result,
            gemini=gemini_result,
            arbiter_results=[],
        )

        # ── Step 4: Gemini arbitration for conflict tokens ─────────────────
        conflicts = consensus_engine.build_conflict_list(word_results)

        if conflicts:
            logger.info(
                f"[{job_id}] {len(conflicts)} conflicts → Gemini arbiter")
            arbiter_results = await self._gemini.arbitrate(
                image_bytes=image_bytes,
                conflicts=conflicts,
            )
            # Re-merge with arbiter decisions applied
            merged_text, word_results = consensus_engine.merge(
                google=google_result,
                azure=azure_result,
                gemini=gemini_result,
                arbiter_results=arbiter_results,
            )
        else:
            logger.info(f"[{job_id}] No conflicts — arbiter not needed")

        # ── Step 5: Build final response ───────────────────────────────────
        conf = consensus_engine.overall_confidence(word_results)
        remaining_conflicts = sum(1 for w in word_results if w.conflict)
        elapsed = int(time.time() * 1000) - start_ms

        logger.info(
            f"[{job_id}] OCR done in {elapsed}ms — "
            f"confidence={conf:.3f}, "
            f"remaining_conflicts={remaining_conflicts}"
        )

        from schemas.ocr import SourceLanguage
        lang = SourceLanguage.SANSKRIT if source_language == "sa" else SourceLanguage.HINDI

        return OCRResponse(
            job_id=job_id,
            merged_text=merged_text,
            word_results=word_results,
            layer_outputs=layer_outputs,
            overall_confidence=conf,
            conflict_count=remaining_conflicts,
            source_language=lang,
            processing_ms=elapsed,
        )
