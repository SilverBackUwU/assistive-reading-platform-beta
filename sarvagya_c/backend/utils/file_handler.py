from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from core.config import get_settings
from core.exceptions import AppError


ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tiff", ".pdf"}
settings = get_settings()


@dataclass(slots=True)
class UploadPayload:
    filename: str
    content_type: str
    content: bytes


async def read_upload(file: UploadFile) -> UploadPayload:
    content = await file.read()
    filename = file.filename or "upload"
    suffix = Path(filename).suffix.lower()

    if not content:
        raise AppError(message="Uploaded file is empty.", status_code=400, code="EMPTY_FILE")
    if suffix not in ALLOWED_EXTENSIONS:
        raise AppError(
            message=f"Unsupported file type '{suffix}'. Use one of: {', '.join(sorted(ALLOWED_EXTENSIONS))}.",
            status_code=422,
            code="UNSUPPORTED_FILE_TYPE",
        )
    if len(content) > settings.max_upload_size_bytes:
        raise AppError(
            message=f"File exceeds {settings.max_upload_size_mb} MB upload limit.",
            status_code=413,
            code="FILE_TOO_LARGE",
        )

    return UploadPayload(
        filename=filename,
        content_type=file.content_type or "application/octet-stream",
        content=content,
    )
