"""Tests for services/api_client.py -- the only module allowed to speak HTTP
to the backend. httpx.request is monkeypatched so no real network call is
made and no real backend needs to be running.
"""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from services.api_client import ApiClient
from services.exceptions import (
    ApiAuthenticationError,
    ApiConnectionError,
    ApiNotFoundError,
    ApiResponseError,
    ApiTimeoutError,
)


def _response(status_code: int, json_body=None, text: str = ""):
    request = httpx.Request("GET", "http://testserver/api/v1/x/")
    return httpx.Response(status_code, json=json_body, text=text if json_body is None else None, request=request)


@pytest.fixture
def client():
    return ApiClient(base_url="http://testserver", timeout=1)


def test_get_returns_json_body(client):
    with patch("services.api_client.httpx.request", return_value=_response(200, {"ok": True})):
        assert client.get("/api/v1/x/") == {"ok": True}


def test_404_raises_not_found(client):
    with patch("services.api_client.httpx.request", return_value=_response(404)):
        with pytest.raises(ApiNotFoundError):
            client.get("/api/v1/missing/")


def test_401_raises_authentication_error(client):
    with patch("services.api_client.httpx.request", return_value=_response(401)):
        with pytest.raises(ApiAuthenticationError):
            client.get("/api/v1/secure/")


def test_500_raises_response_error(client):
    with patch("services.api_client.httpx.request", return_value=_response(500, {"detail": "boom"})):
        with pytest.raises(ApiResponseError):
            client.get("/api/v1/broken/")


def test_connection_error_is_translated(client):
    with patch("services.api_client.httpx.request", side_effect=httpx.ConnectError("refused")):
        with pytest.raises(ApiConnectionError):
            client.get("/api/v1/x/")


def test_timeout_is_translated(client):
    with patch("services.api_client.httpx.request", side_effect=httpx.TimeoutException("slow")):
        with pytest.raises(ApiTimeoutError):
            client.get("/api/v1/x/")


def test_bearer_token_is_sent(client):
    with patch("services.api_client.httpx.request", return_value=_response(200, {})) as mocked:
        client.get("/api/v1/me/", token="abc123")
        _, kwargs = mocked.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer abc123"
