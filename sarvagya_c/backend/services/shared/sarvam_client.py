from __future__ import annotations

from typing import Any

import httpx

from core.config import Settings
from core.exceptions import ConfigurationError, ExternalServiceError


class SarvamClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _build_url(self, endpoint: str) -> str:
        base = str(self._settings.sarvam_base_url).rstrip("/")
        path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        return f"{base}{path}"

    def _headers(self) -> dict[str, str]:
        if not self._settings.sarvam_api_key:
            raise ConfigurationError("SARVAM_API_KEY is missing. Add it to your .env file.")
        return {
            "api-subscription-key": self._settings.sarvam_api_key,
            "Accept": "application/json",
        }

    async def post_json(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = self._build_url(endpoint)
        try:
            async with httpx.AsyncClient(timeout=self._settings.sarvam_timeout_seconds) as client:
                response = await client.post(url, json=payload, headers=self._headers())
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ExternalServiceError(
                message=f"Sarvam request failed with status {exc.response.status_code}: {exc.response.text}",
                status_code=502,
                code="SARVAM_HTTP_ERROR",
            ) from exc
        except httpx.HTTPError as exc:
            raise ExternalServiceError(
                message=f"Unable to reach Sarvam service: {exc}",
                status_code=502,
                code="SARVAM_CONNECTION_ERROR",
            ) from exc

        data = response.json()
        if not isinstance(data, dict):
            raise ExternalServiceError(
                message="Sarvam returned a non-object JSON payload.",
                code="SARVAM_INVALID_RESPONSE",
            )
        return data

    async def post_multipart(
        self,
        endpoint: str,
        files: dict[str, tuple[str, bytes, str]],
        data: dict[str, Any],
    ) -> dict[str, Any]:
        url = self._build_url(endpoint)
        headers = self._headers()
        headers.pop("Accept", None)
        try:
            async with httpx.AsyncClient(timeout=self._settings.sarvam_timeout_seconds) as client:
                response = await client.post(url, data=data, files=files, headers=headers)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ExternalServiceError(
                message=f"Sarvam upload failed with status {exc.response.status_code}: {exc.response.text}",
                status_code=502,
                code="SARVAM_HTTP_ERROR",
            ) from exc
        except httpx.HTTPError as exc:
            raise ExternalServiceError(
                message=f"Unable to reach Sarvam service: {exc}",
                status_code=502,
                code="SARVAM_CONNECTION_ERROR",
            ) from exc

        response_json = response.json()
        if not isinstance(response_json, dict):
            raise ExternalServiceError(
                message="Sarvam returned a non-object JSON payload.",
                code="SARVAM_INVALID_RESPONSE",
            )
        return response_json
