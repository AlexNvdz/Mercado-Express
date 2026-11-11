"""
Colombian departments and cities for the address form. See
../API_CONTRACT.md#apiv1locations.

    GET /api/v1/locations/co/states                 -> [{"code", "name"}], the 33 departments
    GET /api/v1/locations/co/states/{state}/cities  -> ["Medellín", ...]; state = code or name, 404 unknown

Public. The backend reads Envia.com's list and caches it. The address
stores the department's name, and the backend checks the city exists there
(422 otherwise) and fills in the postal code.
"""

from __future__ import annotations

from urllib.parse import quote

from django.conf import settings

from . import mock_data
from .api_client import api_client
from .exceptions import ApiNotFoundError


def list_states() -> list[dict]:
    if settings.API_USE_MOCKS:
        return mock_data.MOCK_STATES
    return api_client.get("/api/v1/locations/co/states")


def list_cities(state: str) -> list[str]:
    """[] for an unknown or empty department."""
    if not state:
        return []
    if settings.API_USE_MOCKS:
        return mock_data.MOCK_CITIES.get(state, [])
    try:
        return api_client.get(f"/api/v1/locations/co/states/{quote(state, safe='')}/cities")
    except ApiNotFoundError:
        return []
