"""
Shipment tracking. See ../API_CONTRACT.md#apiv1shipments.

    POST /api/v1/shipments/order/{order_id}      staff, {"address_id", "carrier"} -> create
    POST /api/v1/shipments/{shipment_id}/ship     staff, no body -> dispatched
    POST /api/v1/shipments/{shipment_id}/deliver  staff, no body -> delivered
    GET  /api/v1/shipments/order/{order_id}

No real carrier is integrated on the backend yet -- tracking numbers are
placeholders (`MANUAL-xxxxxxxxxx`). A 404 on GET just means the order hasn't
reached the `paid`/shipment-created stage yet, not an error to surface.
Response shape confirmed against the real backend (see API_CONTRACT.md):
`{id, order_id, address_id, status, carrier, tracking_number, shipped_at,
delivered_at, created_at, updated_at}`, status
`pending -> preparing -> in_transit -> delivered` (or `failed`/`returned`).
"""

from __future__ import annotations

from django.conf import settings

from . import mock_data
from .api_client import api_client
from .exceptions import ApiNotFoundError

# Mirrors backend-api's ShipmentStatus enum (app/models/enums.py) -- its own
# vocabulary, distinct from OrderStatus (see API_INTEGRATION_NOTES.md).
# Spanish display labels, never render the raw value (see
# apps/core/templatetags/status_labels.py).
SHIPMENT_STATUS_LABELS = {
    "pending": "Pendiente",
    "preparing": "En preparación",
    "in_transit": "En camino",
    "delivered": "Entregado",
    "failed": "Fallido",
    "returned": "Devuelto",
}


def get_shipment_for_order(token: str, order_id: str) -> dict | None:
    if settings.API_USE_MOCKS:
        return mock_data.MOCK_SHIPMENTS.get(str(order_id))

    try:
        return api_client.get(f"/api/v1/shipments/order/{order_id}", token=token)
    except ApiNotFoundError:
        return None


def create_shipment(token: str, order_id: str, address_id: str, carrier: str | None = None) -> dict:
    """Staff only: begin preparing a shipment for a `paid` order."""
    if settings.API_USE_MOCKS:
        shipment = {
            "id": f"mock-ship-{order_id}",
            "order_id": str(order_id),
            "address_id": address_id,
            "status": "preparing",
            "carrier": carrier,
            "tracking_number": "MANUAL-0000000000",
            "shipped_at": None,
            "delivered_at": None,
        }
        mock_data.MOCK_SHIPMENTS[str(order_id)] = shipment
        return shipment
    return api_client.post(
        f"/api/v1/shipments/order/{order_id}", token=token, json={"address_id": address_id, "carrier": carrier}
    )


def ship_shipment(token: str, shipment_id: str, order_id: str) -> dict:
    """Staff only: mark the shipment dispatched (decrements real stock)."""
    if settings.API_USE_MOCKS:
        shipment = mock_data.MOCK_SHIPMENTS.get(str(order_id), {})
        shipment["status"] = "in_transit"
        return shipment
    return api_client.post(f"/api/v1/shipments/{shipment_id}/ship", token=token)


def deliver_shipment(token: str, shipment_id: str, order_id: str) -> dict:
    """Staff only: mark the shipment delivered, closing the order."""
    if settings.API_USE_MOCKS:
        shipment = mock_data.MOCK_SHIPMENTS.get(str(order_id), {})
        shipment["status"] = "delivered"
        return shipment
    return api_client.post(f"/api/v1/shipments/{shipment_id}/deliver", token=token)
