from __future__ import annotations

import re
import tempfile
import zipfile
from pathlib import Path

from core.config import Settings
from core.exceptions import ExternalServiceError
from schemas.ocr import OCRResponse, SourceLanguage
from services.shared.sarvam_client import SarvamClient
from utils.file_handler import UploadPayload
from utils.text_cleaner import clean_ocr_text

try:
    from sarvamai import SarvamAI  # type: ignore
except ImportError:  # pragma: no cover
    SarvamAI = None


class SarvamOCRService:
    def __init__(self, client: SarvamClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    async def extract_text(self, payload: UploadPayload, source_language: SourceLanguage) -> OCRResponse:
        if SarvamAI is None:
            raise ExternalServiceError(
                "The 'sarvamai' package is not installed. Run pip install -r requirements.txt and restart the backend.",
                code="SARVAM_SDK_MISSING",
            )

        language_code = self._language_code(source_language)
        client = SarvamAI(api_subscription_key=self._settings.sarvam_api_key)

        with tempfile.TemporaryDirectory() as tmp_dir:
            workdir = Path(tmp_dir)
            input_path = workdir / payload.filename
            output_path = workdir / "sarvam_ocr_output.zip"
            input_path.write_bytes(payload.content)

            try:
                job = client.document_intelligence.create_job(
                    language=language_code,
                    output_format="md",
                )
                job.upload_file(str(input_path))
                job.start()
                status = job.wait_until_complete()
            except Exception as exc:  # pragma: no cover - SDK specific surface
                raise ExternalServiceError(
                    f"Sarvam OCR job failed to run: {exc}",
                    code="SARVAM_OCR_JOB_FAILED",
                ) from exc

            job_state = str(getattr(status, "job_state", ""))
            if job_state.lower() not in {"completed", "partiallycompleted"}:
                error_message = getattr(status, "error_message", None) or f"Job ended in state '{job_state}'"
                raise ExternalServiceError(
                    error_message,
                    code="SARVAM_OCR_JOB_INCOMPLETE",
                )

            try:
                job.download_output(str(output_path))
                extracted_text = clean_ocr_text(_extract_text_from_zip(output_path))
            except Exception as exc:  # pragma: no cover - SDK specific surface
                raise ExternalServiceError(
                    f"Sarvam OCR output could not be decoded: {exc}",
                    code="SARVAM_OCR_OUTPUT_FAILED",
                ) from exc

            if not extracted_text.strip():
                raise ExternalServiceError(
                    "Sarvam OCR completed but returned empty or corrupted text.",
                    code="SARVAM_OCR_EMPTY_TEXT",
                )

            metrics = _extract_metrics(status, job)
            return OCRResponse(
                source_language=source_language,
                extracted_text=extracted_text.strip(),
                model=self._settings.sarvam_vision_model,
                confidence=None,
                page_count=metrics.get("pages_processed") or metrics.get("total_pages"),
                raw_response={
                    "job_id": str(getattr(status, "job_id", "")),
                    "job_state": job_state,
                    "metrics": metrics,
                },
            )

    def _language_code(self, source_language: SourceLanguage) -> str:
        if source_language == SourceLanguage.HINDI:
            return "hi-IN"
        return "sa-IN"


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


def _extract_metrics(status: object, job: object) -> dict[str, int]:
    metrics: dict[str, int] = {}
    page_metrics = None
    if hasattr(job, "get_page_metrics"):
        try:
            page_metrics = job.get_page_metrics()
        except Exception:
            page_metrics = None

    if isinstance(page_metrics, dict):
        for key in ("total_pages", "pages_processed", "pages_succeeded", "pages_failed"):
            value = page_metrics.get(key)
            if isinstance(value, int):
                metrics[key] = value

    details = getattr(status, "job_details", None)
    if isinstance(details, list) and details:
        first = details[0]
        for key in ("total_pages", "pages_processed", "pages_succeeded", "pages_failed"):
            value = getattr(first, key, None)
            if isinstance(value, int):
                metrics[key] = value
        if isinstance(first, dict):
            for key in ("total_pages", "pages_processed", "pages_succeeded", "pages_failed"):
                value = first.get(key)
                if isinstance(value, int):
                    metrics[key] = value

    for key in ("total_files", "successful_files_count", "failed_files_count"):
        value = getattr(status, key, None)
        if value is None and isinstance(status, dict):
            value = status.get(key)
        if isinstance(value, int):
            metrics[key] = value
    return metrics
