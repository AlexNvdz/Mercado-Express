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

In mock mode, writes mutate the module-level mock_data lists/dicts so a
change is visible on the next read within the same process (mirroring real
persistence) -- see conftest.py for the snapshot/restore fixture that keeps
this from leaking between tests.
"""

from __future__ import annotations

import uuid

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
        mock_data.MOCK_USER.update(payload)
        return mock_data.MOCK_USER
    return api_client.patch("/api/v1/customers/me", token=token, json=payload)


def list_addresses(token: str) -> list[dict]:
    if settings.API_USE_MOCKS:
        return mock_data.MOCK_ADDRESSES
    return api_client.get("/api/v1/customers/me/addresses", token=token)


def add_address(token: str, address: dict) -> dict:
    if settings.API_USE_MOCKS:
        record = {"id": str(uuid.uuid4()), **address}
        mock_data.MOCK_ADDRESSES.append(record)
        return record
    return api_client.post("/api/v1/customers/me/addresses", token=token, json=address)


def update_address(token: str, address_id: str, address: dict) -> dict:
    if settings.API_USE_MOCKS:
        record = next((a for a in mock_data.MOCK_ADDRESSES if a["id"] == str(address_id)), None)
        if record is None:
            raise ApiNotFoundError(f"Address {address_id} not found", status_code=404)
        if address.get("is_default"):
            for other in mock_data.MOCK_ADDRESSES:
                other["is_default"] = False
        record.update(address)
        return record
    return api_client.patch(f"/api/v1/customers/me/addresses/{address_id}", token=token, json=address)


def delete_address(token: str, address_id: str) -> None:
    if settings.API_USE_MOCKS:
        mock_data.MOCK_ADDRESSES[:] = [a for a in mock_data.MOCK_ADDRESSES if a["id"] != str(address_id)]
        return None
    try:
        api_client.delete(f"/api/v1/customers/me/addresses/{address_id}", token=token)
    except ApiNotFoundError:
        pass
