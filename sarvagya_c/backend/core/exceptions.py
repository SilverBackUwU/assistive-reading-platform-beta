from __future__ import annotations

from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from core.logging import get_logger


logger = get_logger(__name__)


@dataclass(slots=True)
class AppError(Exception):
    message: str
    status_code: int = 400
    code: str = "APP_ERROR"


class ConfigurationError(AppError):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=500, code="CONFIGURATION_ERROR")


class ExternalServiceError(AppError):
    def __init__(self, message: str, status_code: int = 502, code: str = "EXTERNAL_SERVICE_ERROR"):
        super().__init__(message=message, status_code=status_code, code=code)


class NotFoundError(AppError):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=404, code="NOT_FOUND")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "code": exc.code},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "code": "INTERNAL_SERVER_ERROR"},
        )
