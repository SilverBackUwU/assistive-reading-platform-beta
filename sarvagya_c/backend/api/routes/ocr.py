from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile

from api.deps import OCRServiceDep
from schemas.ocr import OCRResponse, SourceLanguage
from utils.file_handler import read_upload


router = APIRouter(prefix="/ocr", tags=["OCR"])


@router.post("/extract", response_model=OCRResponse, summary="OCR via Sarvam Vision")
async def extract_text(
    service: OCRServiceDep,
    file: UploadFile = File(...),
    source_language: SourceLanguage = Form(default=SourceLanguage.SANSKRIT),
) -> OCRResponse:
    payload = await read_upload(file)
    return await service.extract_text(payload=payload, source_language=source_language)
