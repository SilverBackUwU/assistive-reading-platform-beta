from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, HttpUrl, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="Sarvagya")
    app_version: str = Field(default="0.2.0")
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)
    api_v1_prefix: str = Field(default="/api/v1")
    log_level: LogLevel = Field(default=LogLevel.INFO)
    cors_origins: str = Field(default="http://localhost:5173,http://localhost:3000")

    upload_dir: Path = Field(default=Path("storage/uploads"))
    output_dir: Path = Field(default=Path("storage/outputs"))
    max_upload_size_mb: int = Field(default=20)

    sarvam_api_key: str = Field(default="")
    sarvam_base_url: HttpUrl = Field(default="https://api.sarvam.ai")
    sarvam_timeout_seconds: float = Field(default=60.0)
    sarvam_vision_endpoint: str = Field(default="/vision/ocr")
    sarvam_translate_endpoint: str = Field(default="/translate")
    sarvam_tts_endpoint: str = Field(default="/text-to-speech")
    sarvam_vision_model: str = Field(default="sarvam-vision")
    sarvam_translate_model: str = Field(default="sarvam-translate")
    sarvam_tts_model: str = Field(default="bulbul")
    sarvam_tts_voice: str = Field(default="meera")
    sarvam_source_language: str = Field(default="sa-IN")
    sarvam_target_language: str = Field(default="en-IN")

    ocr_timeout_seconds: float = Field(default=60.0)
    google_vision_language_hints: str = Field(default="sa,hi")
    azure_doc_intel_endpoint: str = Field(default="")
    azure_doc_intel_key: str = Field(default="")
    azure_doc_intel_model_id: str = Field(default="prebuilt-read")
    azure_doc_intel_language: str = Field(default="sa")
    gemini_api_key: str = Field(default="")
    gemini_model: str = Field(default="gemini-2.5-flash")
    gemini_max_output_tokens: int = Field(default=2048)

    liblouis_table: str = Field(default="en-us-g2.ctb")
    brf_line_width: int = Field(default=32)
    brf_page_height: int = Field(default=25)

    database_url: str = Field(default="")

    @computed_field
    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @computed_field
    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @computed_field
    @property
    def google_vision_language_hints_list(self) -> list[str]:
        return [hint.strip() for hint in self.google_vision_language_hints.split(",") if hint.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
