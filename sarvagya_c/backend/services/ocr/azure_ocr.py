"""
services/ocr/azure_ocr.py
==========================
Layer 2 — Azure Document Intelligence OCR.
Package: azure-ai-documentintelligence==1.0.0

NOTE: This is the NEW SDK (azure-ai-documentintelligence), NOT the old
azure-cognitiveservices-vision-computervision. Import paths are different.

Auth setup:
  1. portal.azure.com → Create resource → Document Intelligence
  2. Copy endpoint URL + Key 1
  3. Set in .env:
       AZURE_DOC_INTEL_ENDPOINT=https://YOUR_RESOURCE.cognitiveservices.azure.com
       AZURE_DOC_INTEL_KEY=your_key_here
"""
from __future__ import annotations

import logging

from schemas.ocr import LayerOutput, OCREngineLabel
from services.ocr.base import OCREngine

logger = logging.getLogger(__name__)


class AzureDocumentOCR(OCREngine):
    """
    Uses Azure Document Intelligence prebuilt-read model.
    prebuilt-read explicitly supports Sanskrit (language code: sa).
    Returns structured paragraphs joined as full text.
    """

    def __init__(self, endpoint: str, key: str, model_id: str, language: str):
        self._endpoint = endpoint
        self._key = key
        self._model_id = model_id    # "prebuilt-read"
        self._language = language    # "sa" for Sanskrit
        self._client = None        # lazy init

    @property
    def engine_name(self) -> str:
        return OCREngineLabel.AZURE

    def _get_client(self):
        if self._client is None:
            try:
                from azure.ai.documentintelligence import DocumentIntelligenceClient
                from azure.core.credentials import AzureKeyCredential

                self._client = DocumentIntelligenceClient(
                    endpoint=self._endpoint,
                    credential=AzureKeyCredential(self._key),
                )
                logger.info("Azure Document Intelligence client initialised")
            except Exception as e:
                raise RuntimeError(
                    f"Azure client failed to initialise: {e}\n"
                    f"Check AZURE_DOC_INTEL_ENDPOINT and AZURE_DOC_INTEL_KEY in .env"
                ) from e
        return self._client

    async def extract(self, image_bytes: bytes) -> LayerOutput:
        try:
            import io
            from azure.ai.documentintelligence.models import AnalyzeDocumentRequest

            client = self._get_client()

            # Azure SDK is synchronous — wrap bytes in BytesIO
            poller = client.begin_analyze_document(
                model_id=self._model_id,
                analyze_request=AnalyzeDocumentRequest(
                    bytes_source=image_bytes
                ),
                locale=self._language,   # "sa" = Sanskrit
                content_type="application/octet-stream",
            )
            result = poller.result()

            if not result or not result.content:
                return LayerOutput(
                    engine=OCREngineLabel.AZURE,
                    text="",
                    confidence=0.0,
                    success=False,
                    error="Azure returned empty content",
                )

            # result.content is the full extracted text
            # result.paragraphs gives structured paragraphs — we use content
            # for simplicity (same data, already newline-separated)
            full_text = result.content.strip()

            # Azure exposes per-word confidence in result.pages[].words[]
            confidence = _compute_azure_confidence(result)

            logger.info(
                f"Azure OCR: {len(full_text)} chars, "
                f"confidence={confidence:.3f}"
            )
            return LayerOutput(
                engine=OCREngineLabel.AZURE,
                text=full_text,
                confidence=confidence,
                success=True,
            )

        except Exception as e:
            logger.error(f"Azure OCR failed: {e}")
            return LayerOutput(
                engine=OCREngineLabel.AZURE,
                text="",
                confidence=0.0,
                success=False,
                error=str(e),
            )


def _compute_azure_confidence(result) -> float:
    """
    Average confidence across all words in all pages.
    Azure Document Intelligence exposes per-word confidence scores.
    """
    scores = []
    try:
        for page in result.pages or []:
            for word in page.words or []:
                if word.confidence is not None:
                    scores.append(word.confidence)
    except Exception:
        pass
    if not scores:
        return 0.87  # Azure default fallback
    return round(sum(scores) / len(scores), 4)
