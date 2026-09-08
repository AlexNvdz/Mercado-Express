"""
Thin HTTP client for the MercadoExpress FastAPI backend.

This is the ONLY module in the project allowed to make HTTP calls to the
backend API. Everything else (services/*.py, and every Django view/template)
must go through the higher-level service modules, never through httpx
directly.

    apps.catalog.views  ->  services.products  ->  services.api_client  ->  FastAPI

Configuration comes exclusively from environment variables (see
config/settings/base.py: MERCADOEXPRESS_API_BASE_URL, API_TIMEOUT_SECONDS via
settings.API_BASE_URL / settings.API_TIMEOUT_SECONDS). No URL is hardcoded
here or anywhere else in the project.

Contract: ../API_CONTRACT.md (maintained by backend-api).
"""

from __future__ import annotations

from typing import Any

import httpx
from django.conf import settings

from .exceptions import (
    ApiAuthenticationError,
    ApiConflictError,
    ApiConnectionError,
    ApiError,
    ApiNotFoundError,
    ApiPermissionError,
    ApiResponseError,
    ApiTimeoutError,
    ApiValidationError,
)

_ERROR_CLASS_BY_STATUS = {
    401: ApiAuthenticationError,
    403: ApiPermissionError,
    404: ApiNotFoundError,
    409: ApiConflictError,
    422: ApiValidationError,
}


class ApiClient:
    """Small wrapper around httpx that centralizes base URL, timeouts,
    auth-token handling, and error translation for calls to the backend API.
    """

    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        self.base_url = (base_url or settings.API_BASE_URL).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.API_TIMEOUT_SECONDS

    def _headers(self, token: str | None) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> Any:
        """Perform an HTTP request against the backend API and return the
        decoded JSON body. Raises a subclass of ApiError on any failure.

        `json` sends an `application/json` body; `data` sends a form-encoded
        (`application/x-www-form-urlencoded`) body -- the backend's
        `/auth/login` requires the latter (OAuth2-password-compatible).
        """
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            response = httpx.request(
                method,
                url,
                params=params,
                json=json,
                data=data,
                headers=self._headers(token),
                timeout=self.timeout,
            )
        except httpx.TimeoutException as exc:
            raise ApiTimeoutError(f"Timed out calling {url}") from exc
        except httpx.RequestError as exc:
            raise ApiConnectionError(f"Could not reach backend API at {url}: {exc}") from exc

        if response.status_code >= 400:
            try:
                payload = response.json()
            except ValueError:
                payload = {"detail": response.text}
            error_cls = _ERROR_CLASS_BY_STATUS.get(response.status_code, ApiResponseError)
            raise error_cls(
                f"Backend API returned {response.status_code} for {url}",
                status_code=response.status_code,
                payload=payload,
            )

        if not response.content:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise ApiError(f"Backend API returned invalid JSON for {url}") from exc

    def get(self, path: str, **kwargs: Any) -> Any:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> Any:
        return self.request("POST", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> Any:
        return self.request("PATCH", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> Any:
        return self.request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Any:
        return self.request("DELETE", path, **kwargs)


# Shared default instance. Individual service modules import this rather than
# constructing their own ApiClient, so base_url/timeout config stays uniform.
api_client = ApiClient()
