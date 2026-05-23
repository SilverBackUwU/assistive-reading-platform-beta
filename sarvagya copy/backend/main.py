from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import braille, metadata, ocr, pipeline, translation, tts
from core.config import get_settings
from core.exceptions import register_exception_handlers
from core.logging import configure_logging, get_logger


settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    yield
    logger.info("Stopping %s", settings.app_name)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Sarvagya Assistive Reading Platform. Upload an image or PDF, "
            "run a multi-OCR ensemble over the source text, translate it to "
            "English, generate Grade 2 Braille, and synthesize read-aloud audio."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(metadata.router)
    app.include_router(ocr.router, prefix=settings.api_v1_prefix)
    app.include_router(translation.router, prefix=settings.api_v1_prefix)
    app.include_router(braille.router, prefix=settings.api_v1_prefix)
    app.include_router(tts.router, prefix=settings.api_v1_prefix)
    app.include_router(pipeline.router, prefix=settings.api_v1_prefix)
    return app


app = create_app()


@app.get("/")
async def root():
    return {"message": "Sharvagya Backend Running"}
