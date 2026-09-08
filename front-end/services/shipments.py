"""
Shipment tracking. See ../API_CONTRACT.md#apiv1shipments.

    GET /api/v1/shipments/order/{order_id}

No real carrier is integrated on the backend yet -- tracking numbers are
placeholders (`MANUAL-xxxxxxxxxx`). A 404 here just means the order hasn't
reached the `paid`/shipment-created stage yet, not an error to surface.

NOTE: API_CONTRACT.md documents the POST request body for creating a
shipment but not the GET response shape. See API_INTEGRATION_NOTES.md
(ENDPOINT SOLICITADO) for the field names assumed below (carrier,
tracking_number, status, shipped_at, delivered_at) pending confirmation.
"""

from __future__ import annotations

from django.conf import settings

from . import mock_data
from .api_client import api_client
from .exceptions import ApiNotFoundError


def get_shipment_for_order(token: str, order_id: str) -> dict | None:
    if settings.API_USE_MOCKS:
        return mock_data.MOCK_SHIPMENTS.get(str(order_id))

    try:
        return api_client.get(f"/api/v1/shipments/order/{order_id}", token=token)
    except ApiNotFoundError:
        return None
