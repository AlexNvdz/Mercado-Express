"""
Stock availability. See ../API_CONTRACT.md#apiv1inventory.

    GET  /api/v1/inventory/{product_id}
    POST /api/v1/inventory/{product_id}/adjust   staff, {"delta": int, "reason": str|None}
    PUT  /api/v1/inventory/{product_id}          staff, {"quantity_on_hand": int, "reorder_level": int|None}

Stock is a separate resource from the product itself (single stock pool per
product on the backend); this module is the only place that reads/writes it.
`delta` is signed: positive restocks, negative removes (shrinkage,
correction) -- confirmed against backend-api/app/schemas/inventory.py.
"""

from __future__ import annotations

from django.conf import settings

from . import mock_data
from .api_client import api_client
from .exceptions import ApiNotFoundError


def get_availability(product_id: str) -> dict | None:
    """Returns {"quantity_on_hand", "quantity_reserved", "quantity_available",
    "reorder_level", ...} or None if the product has no inventory row.
    """
    if settings.API_USE_MOCKS:
        record = mock_data.MOCK_INVENTORY.get(str(product_id))
        if record is None:
            return None
        on_hand = record["quantity_on_hand"]
        reserved = record["quantity_reserved"]
        return {
            "product_id": str(product_id),
            "quantity_on_hand": on_hand,
            "quantity_reserved": reserved,
            "quantity_available": on_hand - reserved,
            "reorder_level": record.get("reorder_level", 0),
        }

    try:
        return api_client.get(f"/api/v1/inventory/{product_id}")
    except ApiNotFoundError:
        return None


def adjust_stock(token: str, product_id: str, delta: int, reason: str | None = None) -> dict:
    """Add (delta > 0) or remove (delta < 0) stock -- restock/shrinkage/correction."""
    if settings.API_USE_MOCKS:
        record = mock_data.MOCK_INVENTORY.setdefault(
            str(product_id), {"quantity_on_hand": 0, "quantity_reserved": 0, "reorder_level": 0}
        )
        record["quantity_on_hand"] = max(0, record["quantity_on_hand"] + delta)
        return get_availability(product_id)

    payload = {"delta": delta, "reason": reason}
    return api_client.post(f"/api/v1/inventory/{product_id}/adjust", token=token, json=payload)


def set_levels(token: str, product_id: str, quantity_on_hand: int, reorder_level: int | None = None) -> dict:
    """Set absolute on-hand/reorder levels (inventory count correction)."""
    if settings.API_USE_MOCKS:
        record = mock_data.MOCK_INVENTORY.setdefault(
            str(product_id), {"quantity_on_hand": 0, "quantity_reserved": 0, "reorder_level": 0}
        )
        record["quantity_on_hand"] = quantity_on_hand
        if reorder_level is not None:
            record["reorder_level"] = reorder_level
        return get_availability(product_id)

    payload = {"quantity_on_hand": quantity_on_hand, "reorder_level": reorder_level}
    return api_client.put(f"/api/v1/inventory/{product_id}", token=token, json=payload)
