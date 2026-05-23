from __future__ import annotations

from fastapi import APIRouter, File, Form, Path, UploadFile

from api.deps import PipelineServiceDep
from schemas.ocr import SourceLanguage
from schemas.pipeline import PipelineResponse
from utils.file_handler import read_upload


router = APIRouter(prefix="/pipeline", tags=["Pipeline"])


@router.post("/run", response_model=PipelineResponse, summary="Run full assistive pipeline with OCR ensemble")
async def run_pipeline(
    service: PipelineServiceDep,
    file: UploadFile = File(...),
    source_language: SourceLanguage = Form(default=SourceLanguage.SANSKRIT),
) -> PipelineResponse:
    payload = await read_upload(file)
    return await service.run(payload=payload, source_language=source_language)


@router.get("/jobs/{job_id}", response_model=PipelineResponse, summary="Get pipeline job result")
async def get_pipeline_job(
    service: PipelineServiceDep,
    job_id: str = Path(..., description="Job identifier returned by /pipeline/run"),
) -> PipelineResponse:
    return service.get_job(job_id)
