"""
Customer profile and address book. See ../API_CONTRACT.md#apiv1customers.

    GET   /api/v1/customers/me
    PATCH /api/v1/customers/me                          {full_name?, phone?}
    GET   /api/v1/customers/me/addresses
    POST  /api/v1/customers/me/addresses
    PATCH /api/v1/customers/me/addresses/{address_id}
    DELETE /api/v1/customers/me/addresses/{address_id}

Addresses matter beyond profile display: order creation requires a
`shipping_address_id` (see services/orders.create_order), so checkout routes
customers here first if they have none saved yet.
"""

from __future__ import annotations

from django.conf import settings

from . import mock_data
from .api_client import api_client
from .exceptions import ApiNotFoundError


def get_profile(token: str) -> dict | None:
    if settings.API_USE_MOCKS:
        return mock_data.MOCK_USER if token else None
    return api_client.get("/api/v1/customers/me", token=token)


def update_profile(token: str, *, full_name: str | None = None, phone: str | None = None) -> dict:
    payload = {k: v for k, v in {"full_name": full_name, "phone": phone}.items() if v is not None}
    if settings.API_USE_MOCKS:
        return {**mock_data.MOCK_USER, **payload}
    return api_client.patch("/api/v1/customers/me", token=token, json=payload)


def list_addresses(token: str) -> list[dict]:
    if settings.API_USE_MOCKS:
        return mock_data.MOCK_ADDRESSES
    return api_client.get("/api/v1/customers/me/addresses", token=token)


def add_address(token: str, address: dict) -> dict:
    if settings.API_USE_MOCKS:
        return {"id": f"mock-addr-{len(mock_data.MOCK_ADDRESSES) + 1}", **address}
    return api_client.post("/api/v1/customers/me/addresses", token=token, json=address)


def update_address(token: str, address_id: str, address: dict) -> dict:
    if settings.API_USE_MOCKS:
        return {"id": address_id, **address}
    return api_client.patch(f"/api/v1/customers/me/addresses/{address_id}", token=token, json=address)


def delete_address(token: str, address_id: str) -> None:
    if settings.API_USE_MOCKS:
        return None
    try:
        api_client.delete(f"/api/v1/customers/me/addresses/{address_id}", token=token)
    except ApiNotFoundError:
        pass
