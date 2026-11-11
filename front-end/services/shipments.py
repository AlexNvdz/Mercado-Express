"""
Shipment tracking. See ../API_CONTRACT.md#apiv1shipments.

    POST  /api/v1/shipments/order/{order_id}      staff, {"address_id", "carrier", "tracking_number"} -> create
    PATCH /api/v1/shipments/{shipment_id}         staff, {"carrier", "tracking_number"} -> edit before dispatch
    POST  /api/v1/shipments/{shipment_id}/ship     staff, no body -> dispatched
    POST  /api/v1/shipments/{shipment_id}/deliver  staff, no body -> delivered
    POST  /api/v1/shipments/order/{order_id}/envia staff, no body -> cheapest Envia label + shipment
    POST  /api/v1/shipments/{shipment_id}/sync     staff, no body -> shipment + "carrier_status"
    GET   /api/v1/shipments/order/{order_id}

Envia.com: with it configured, the backend buys the cheapest label on its
own right after the payment; `/envia` is the panel's retry when that failed
(502 when Envia fails, 422 when the address/phone isn't usable, 409 if the
order already has a shipment). `/sync` reads the carrier's tracking and
dispatches/delivers the shipment if the carrier says so. An Envia shipment
also has `service`, `label_url`, `tracking_url` and `shipping_cost` (null
otherwise; the customer's GET gets `label_url`/`shipping_cost` as null), and
its carrier/tracking number can't be edited (409).

A shipment can be created while the order is `paid` or `preparing` (staff
may have moved it to `preparing` by hand first; 409 otherwise, or if it
already has one), and its carrier/tracking number stay editable until it is
dispatched (PATCH sends only the keys to change; null/blank clears). A
tracking number left empty is generated as `MANUAL-xxxxxxxxxx` at dispatch.
Dispatch (order must be `preparing`) and delivery are the only way an order
reaches `shipped`/`delivered`. A 404 on GET just means the order has no
shipment yet, not an error to surface.
Response shape confirmed against the real backend (see API_CONTRACT.md):
`{id, order_id, address_id, status, carrier, tracking_number, shipped_at,
delivered_at, created_at, updated_at}`, status
`pending -> preparing -> in_transit -> delivered` (or `failed`/`returned`,
or `cancelled` when the order is cancelled/refunded before dispatch).
"""

from __future__ import annotations

from django.conf import settings

from . import mock_data
from .api_client import ApiClient, api_client
from .exceptions import ApiConflictError, ApiNotFoundError

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
    "cancelled": "Cancelado",
}

# Order statuses from which staff can create a shipment, and shipment
# statuses in which carrier/tracking number can still be edited (i.e. not
# dispatched yet). Mirror backend-api's ShipmentService checks.
SHIPMENT_CREATABLE_ORDER_STATUSES = ("paid", "preparing")

# The backend gives each Envia call up to 30 s (ENVIA_TIMEOUT_SECONDS).
_envia_client = ApiClient(timeout=65)
SHIPMENT_EDITABLE_STATUSES = ("pending", "preparing")


def can_create_shipment(order_status: str) -> bool:
    return order_status in SHIPMENT_CREATABLE_ORDER_STATUSES


def is_editable(shipment: dict) -> bool:
    return shipment["status"] in SHIPMENT_EDITABLE_STATUSES and not shipment.get("label_url")


def can_sync(shipment: dict) -> bool:
    """An Envia label still on its way."""
    return bool(shipment.get("label_url")) and shipment["status"] in ("preparing", "in_transit")


def get_shipment_for_order(token: str, order_id: str) -> dict | None:
    if settings.API_USE_MOCKS:
        return mock_data.MOCK_SHIPMENTS.get(str(order_id))

    try:
        return api_client.get(f"/api/v1/shipments/order/{order_id}", token=token)
    except ApiNotFoundError:
        return None


def create_shipment(
    token: str,
    order_id: str,
    address_id: str,
    carrier: str | None = None,
    tracking_number: str | None = None,
) -> dict:
    """Staff only: start a shipment for a `paid` or `preparing` order. The
    order ends up `preparing`.
    """
    if settings.API_USE_MOCKS:
        order = _mock_order(order_id)
        if not can_create_shipment(order["status"]) or str(order_id) in mock_data.MOCK_SHIPMENTS:
            raise ApiConflictError("Shipment cannot be created for this order.", status_code=409)
        shipment = {
            "id": f"mock-ship-{order_id}",
            "order_id": str(order_id),
            "address_id": address_id,
            "status": "preparing",
            "carrier": carrier,
            "tracking_number": tracking_number,
            "shipped_at": None,
            "delivered_at": None,
        }
        mock_data.MOCK_SHIPMENTS[str(order_id)] = shipment
        order["status"] = "preparing"
        return shipment
    return api_client.post(
        f"/api/v1/shipments/order/{order_id}",
        token=token,
        json={"address_id": address_id, "carrier": carrier, "tracking_number": tracking_number},
    )


def update_shipment(
    token: str, shipment_id: str, order_id: str, *, carrier: str | None, tracking_number: str | None
) -> dict:
    """Staff only: change carrier/tracking number before dispatch (409 after)."""
    if settings.API_USE_MOCKS:
        shipment = mock_data.MOCK_SHIPMENTS.get(str(order_id))
        if shipment is None:
            raise ApiNotFoundError("Shipment not found.", status_code=404)
        if not is_editable(shipment):
            raise ApiConflictError("Shipment already dispatched.", status_code=409)
        shipment["carrier"] = carrier
        shipment["tracking_number"] = tracking_number
        return shipment
    return api_client.patch(
        f"/api/v1/shipments/{shipment_id}",
        token=token,
        json={"carrier": carrier, "tracking_number": tracking_number},
    )


def ship_shipment(token: str, shipment_id: str, order_id: str) -> dict:
    """Staff only: mark the shipment dispatched (decrements real stock); the
    order must be `preparing` and moves to `shipped`.
    """
    if settings.API_USE_MOCKS:
        shipment = mock_data.MOCK_SHIPMENTS.get(str(order_id), {})
        order = _mock_order(order_id)
        if shipment.get("status") != "preparing" or order["status"] != "preparing":
            raise ApiConflictError("Shipment cannot be dispatched.", status_code=409)
        shipment["status"] = "in_transit"
        shipment["tracking_number"] = shipment["tracking_number"] or "MANUAL-0000000000"
        order["status"] = "shipped"
        return shipment
    return api_client.post(f"/api/v1/shipments/{shipment_id}/ship", token=token)


def deliver_shipment(token: str, shipment_id: str, order_id: str) -> dict:
    """Staff only: mark the shipment delivered; the order moves to `delivered`."""
    if settings.API_USE_MOCKS:
        shipment = mock_data.MOCK_SHIPMENTS.get(str(order_id), {})
        shipment["status"] = "delivered"
        _mock_order(order_id)["status"] = "delivered"
        return shipment
    return api_client.post(f"/api/v1/shipments/{shipment_id}/deliver", token=token)


def create_envia_shipment(token: str, order_id: str) -> dict:
    """Staff only: buy the cheapest Envia label for the order and create its
    shipment. Waits on two Envia calls, so it gets a longer timeout."""
    if settings.API_USE_MOCKS:
        order = _mock_order(order_id)
        if not can_create_shipment(order["status"]) or str(order_id) in mock_data.MOCK_SHIPMENTS:
            raise ApiConflictError("Shipment cannot be created for this order.", status_code=409)
        shipment = {
            "id": f"mock-ship-{order_id}",
            "order_id": str(order_id),
            "address_id": order["shipping_address_id"],
            "status": "preparing",
            "carrier": "interRapidisimo",
            "service": "ground",
            "tracking_number": "INTESBX000001",
            "tracking_url": "https://envia.com/rastreo?label=INTESBX000001",
            "label_url": "https://example.com/guia-INTESBX000001.pdf",
            "shipping_cost": "8500.00",
            "shipped_at": None,
            "delivered_at": None,
        }
        mock_data.MOCK_SHIPMENTS[str(order_id)] = shipment
        order["status"] = "preparing"
        return shipment
    return _envia_client.post(f"/api/v1/shipments/order/{order_id}/envia", token=token)


def retry_envia_shipments(token: str) -> dict:
    """Staff only: buy the missing label of up to 10 paid Colombian orders.
    `{created, failed: [{order_id, order_number, detail}], remaining}`."""
    if settings.API_USE_MOCKS:
        created = 0
        for order in mock_data.MOCK_ORDERS:
            if order["status"] == "paid" and (order.get("shipping_address") or {}).get("country") == "CO":
                create_envia_shipment(token, order["id"])
                created += 1
        return {"created": created, "failed": [], "remaining": 0}
    # shortcut: one 65 s timeout for the whole batch; the backend caps it at 10 orders.
    return _envia_client.post("/api/v1/shipments/envia/retry", token=token)


def sync_shipment(token: str, shipment_id: str, order_id: str) -> dict:
    """Staff only: the shipment after reading Envia's tracking, plus
    `carrier_status` (Envia's own status name, e.g. "Created")."""
    if settings.API_USE_MOCKS:
        shipment = mock_data.MOCK_SHIPMENTS.get(str(order_id))
        if shipment is None:
            raise ApiNotFoundError("Shipment not found.", status_code=404)
        return {**shipment, "carrier_status": "Created"}
    return _envia_client.post(f"/api/v1/shipments/{shipment_id}/sync", token=token)


def _mock_order(order_id: str) -> dict:
    order = next((o for o in mock_data.MOCK_ORDERS if o["id"] == str(order_id)), None)
    if order is None:
        raise ApiNotFoundError("Order not found.", status_code=404)
    return order
