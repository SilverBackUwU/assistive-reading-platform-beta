from __future__ import annotations

import asyncio
import logging
import re
import tempfile
import zipfile
from pathlib import Path

from core.config import Settings
from core.exceptions import ExternalServiceError
from schemas.ocr import OCRResponse, SourceLanguage
from utils.file_handler import UploadPayload
from utils.text_cleaner import clean_ocr_text, preview_ocr_text

try:
    from sarvamai import SarvamAI  # type: ignore
except ImportError:  # pragma: no cover
    SarvamAI = None


logger = logging.getLogger(__name__)


class SarvamOCRService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def extract(self, payload: UploadPayload, source_language: SourceLanguage) -> dict[str, object]:
        return await self.extract_bytes(
            content=payload.content,
            filename=payload.filename or "upload",
            source_language=source_language,
        )

    async def extract_bytes(
        self,
        content: bytes,
        filename: str,
        source_language: SourceLanguage,
    ) -> dict[str, object]:
        try:
            text = await asyncio.to_thread(self._extract_sync, content, filename, source_language)
            confidence = self._confidence_for(text)
            return {"engine": "sarvam", "text": text, "confidence": confidence}
        except Exception as exc:
            logger.warning("Sarvam OCR failed: %s", exc)
            return {"engine": "sarvam", "text": "", "confidence": 0.0}

    async def extract_text(self, payload: UploadPayload, source_language: SourceLanguage) -> OCRResponse:
        candidate = await self.extract(payload=payload, source_language=source_language)
        extracted_text = str(candidate.get("text") or "")
        if not extracted_text.strip():
            raise ExternalServiceError(
                "Sarvam OCR did not return any text.",
                code="SARVAM_OCR_EMPTY_TEXT",
            )

        return OCRResponse(
            source_language=source_language,
            extracted_text=extracted_text,
            model=self._settings.sarvam_vision_model,
            confidence=float(candidate.get("confidence") or 0.0),
            page_count=None,
            raw_response={"engine": "sarvam"},
        )

    def _extract_sync(self, content: bytes, filename: str, source_language: SourceLanguage) -> str:
        if SarvamAI is None:
            raise RuntimeError(
                "The 'sarvamai' package is not installed. Run pip install -r requirements.txt and restart the backend."
            )
        if not self._settings.sarvam_api_key:
            raise RuntimeError("SARVAM_API_KEY is missing. Add it to your .env file.")

        language_code = self._language_code(source_language)
        client = SarvamAI(api_subscription_key=self._settings.sarvam_api_key)
        safe_name = Path(filename).name or "upload.png"

        with tempfile.TemporaryDirectory() as tmp_dir:
            workdir = Path(tmp_dir)
            input_path = workdir / safe_name
            output_path = workdir / "sarvam_ocr_output.zip"
            input_path.write_bytes(content)

            job = client.document_intelligence.create_job(
                language=language_code,
                output_format="md",
            )
            job.upload_file(str(input_path))
            job.start()
            status = job.wait_until_complete()

            job_state = str(getattr(status, "job_state", ""))
            if job_state.lower() not in {"completed", "partiallycompleted"}:
                error_message = getattr(status, "error_message", None) or f"Job ended in state '{job_state}'"
                raise RuntimeError(error_message)

            job.download_output(str(output_path))
            extracted_text = clean_ocr_text(_extract_text_from_zip(output_path))
            logger.debug("Sarvam OCR cleaned response preview: %s", preview_ocr_text(extracted_text))
            if not extracted_text.strip():
                raise RuntimeError("Sarvam OCR completed but returned empty or corrupted text.")
            return extracted_text.strip()

    def _language_code(self, source_language: SourceLanguage) -> str:
        if source_language == SourceLanguage.HINDI:
            return "hi-IN"
        return "sa-IN"

    def _confidence_for(self, text: str) -> float:
        if not text.strip():
            return 0.0
        return 0.86


def _extract_text_from_zip(zip_path: Path) -> str:
    with zipfile.ZipFile(zip_path) as archive:
        candidates = [
            name for name in archive.namelist()
            if name.lower().endswith((".md", ".txt", ".html", ".htm"))
        ]
        if not candidates:
            raise ExternalServiceError(
                "Sarvam OCR ZIP output did not contain a readable text file.",
                code="SARVAM_OCR_NO_TEXT_FILE",
            )

        preferred = sorted(candidates, key=_text_sort_key)[0]
        content = archive.read(preferred).decode("utf-8", errors="ignore")
        if preferred.lower().endswith((".html", ".htm")):
            content = _strip_html(content)
        return content


def _text_sort_key(name: str) -> tuple[int, str]:
    lower = name.lower()
    priority = 0 if lower.endswith(".md") else 1 if lower.endswith(".txt") else 2
    return (priority, lower)


def _strip_html(value: str) -> str:
    value = re.sub(r"<script.*?</script>", "", value, flags=re.I | re.S)
    value = re.sub(r"<style.*?</style>", "", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()
