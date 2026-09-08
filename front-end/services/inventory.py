"""
Stock availability. See ../API_CONTRACT.md#apiv1inventory.

Stock is a separate resource from the product itself (single stock pool per
product on the backend); this module is the only place that reads it.
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
