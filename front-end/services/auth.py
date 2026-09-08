"""
Customer authentication against the backend API.
See ../API_CONTRACT.md#authentication:

    POST /api/v1/auth/register   json {email, password, full_name, phone}
    POST /api/v1/auth/login      form-encoded {username=email, password} -> token pair
    POST /api/v1/auth/refresh    json {refresh_token} -> new access token
    GET  /api/v1/auth/me         Bearer token -> current user

Django's own auth.User / session framework is NOT the source of truth for
customer identity: the session only stores the JWT access/refresh token pair
(settings.API_ACCESS_TOKEN_SESSION_KEY / API_REFRESH_TOKEN_SESSION_KEY) so
subsequent requests can call the backend on the visitor's behalf. Do not add
password fields or a competing user model here.
"""

from __future__ import annotations

from django.conf import settings

from . import mock_data
from .api_client import api_client
from .exceptions import ApiAuthenticationError


def register(email: str, password: str, full_name: str, phone: str | None = None) -> dict:
    """Return the created customer, or raise ApiError (e.g. ApiConflictError
    on duplicate email) on failure.
    """
    if settings.API_USE_MOCKS:
        return {**mock_data.MOCK_USER, "email": email, "full_name": full_name, "phone": phone}

    return api_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": full_name, "phone": phone},
    )


def login(email: str, password: str) -> dict:
    """Return {"access_token", "refresh_token", "token_type"} or raise
    ApiAuthenticationError. Login is form-encoded per OAuth2-password spec.
    """
    if settings.API_USE_MOCKS:
        if email == mock_data.MOCK_USER["email"] and password == "demo1234":
            return {
                "access_token": "mock-access-token",
                "refresh_token": "mock-refresh-token",
                "token_type": "bearer",
            }
        raise ApiAuthenticationError("Credenciales inválidas", status_code=401)

    return api_client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )


def refresh_access_token(refresh_token: str) -> dict:
    """Return a fresh {"access_token", ...}, or raise ApiAuthenticationError
    if the refresh token itself is invalid/expired.
    """
    if settings.API_USE_MOCKS:
        return {"access_token": "mock-access-token", "token_type": "bearer"}

    return api_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})


def get_current_user(token: str) -> dict | None:
    if settings.API_USE_MOCKS:
        return mock_data.MOCK_USER if token else None

    try:
        return api_client.get("/api/v1/auth/me", token=token)
    except ApiAuthenticationError:
        return None


# --- Session helpers -------------------------------------------------------


def save_tokens(request, *, access_token: str, refresh_token: str | None = None) -> None:
    request.session[settings.API_ACCESS_TOKEN_SESSION_KEY] = access_token
    if refresh_token is not None:
        request.session[settings.API_REFRESH_TOKEN_SESSION_KEY] = refresh_token


def get_access_token(request) -> str | None:
    return request.session.get(settings.API_ACCESS_TOKEN_SESSION_KEY)


def get_refresh_token(request) -> str | None:
    return request.session.get(settings.API_REFRESH_TOKEN_SESSION_KEY)


def clear_tokens(request) -> None:
    request.session.pop(settings.API_ACCESS_TOKEN_SESSION_KEY, None)
    request.session.pop(settings.API_REFRESH_TOKEN_SESSION_KEY, None)


def is_authenticated(request) -> bool:
    return bool(get_access_token(request))
