"""
Order creation, listing, detail and cancellation. See
../API_CONTRACT.md#apiv1orders.

    POST /api/v1/orders                       {items, shipping_address_id, notes}
    GET  /api/v1/orders?page=&page_size=      -> own orders (customer) / all (staff)
    GET  /api/v1/orders/{order_id}
    POST  /api/v1/orders/{order_id}/cancel
    PATCH /api/v1/orders/{order_id}/status    staff, {"status": "<OrderStatus>"}

No order/pricing/inventory business logic is duplicated here: this module
only shapes requests/responses for the views. Totals, stock reservation and
status transitions are computed by FastAPI; a 409 means out-of-stock or an
invalid status transition (see services.exceptions.ApiConflictError).
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from django.conf import settings

from . import mock_data
from .api_client import api_client
from .exceptions import ApiConflictError, ApiNotFoundError

# Mirrors backend-api's OrderStatus enum (app/models/enums.py). 7 statuses
# total -- no separate "awaiting_payment" (removed 2026-09-12: a failed
# payment leaves the order "pending", already retryable from there). Used to
# populate the staff status-override form in apps/adminpanel.
ORDER_STATUSES = [
    "pending",
    "paid",
    "preparing",
    "shipped",
    "delivered",
    "cancelled",
    "refunded",
]

# Spanish display labels -- the values above stay in English (they're the
# API's wire vocabulary, used as-is in querystrings/CSS classes/PATCH
# bodies); never render a raw value to a user, always go through this map
# (see apps/core/templatetags/status_labels.py).
ORDER_STATUS_LABELS = {
    "pending": "Pendiente",
    "paid": "Pagado",
    "preparing": "En preparación",
    "shipped": "Enviado",
    "delivered": "Entregado",
    "cancelled": "Cancelado",
    "refunded": "Reembolsado",
}

# Mirrors backend-api's order_service._ALLOWED_TRANSITIONS
# (app/services/order_service.py): the manual status override only offers
# what the backend accepts, anything else is a 409. Only corrections live
# here -- "paid" comes from a completed payment (POST /payments), "shipped"
# and "delivered" only from the shipment dispatch/deliver steps
# (services/shipments.py), so none of them is a manual-override target.
ORDER_TRANSITIONS = {
    "pending": ["cancelled"],
    "paid": ["preparing", "cancelled", "refunded"],
    "preparing": ["cancelled"],
    "shipped": [],
    "delivered": [],
    "cancelled": [],
    "refunded": [],
}


def next_statuses(current_status: str) -> list[str]:
    """Valid next values for the manual status-override form, given the
    order's current status. Empty for shipped (only the shipment's deliver
    step moves it on) and for terminal states (delivered/cancelled/refunded).
    """
    return ORDER_TRANSITIONS.get(current_status, [])


def list_orders(token: str, *, page: int = 1, page_size: int = 20) -> dict:
    if settings.API_USE_MOCKS:
        items = mock_data.MOCK_ORDERS
        return {"items": items, "total": len(items), "page": 1, "page_size": len(items), "pages": 1}
    return api_client.get("/api/v1/orders", token=token, params={"page": page, "page_size": page_size})


def get_order(token: str, order_id: str) -> dict | None:
    if settings.API_USE_MOCKS:
        return next((o for o in mock_data.MOCK_ORDERS if o["id"] == str(order_id)), None)

    try:
        return api_client.get(f"/api/v1/orders/{order_id}", token=token)
    except ApiNotFoundError:
        return None


def create_order(token: str, items: list[dict], shipping_address_id: str, notes: str | None = None) -> dict:
    """items: [{"product_id": "<uuid>", "quantity": int}, ...]

    The backend validates stock, reserves it and computes totals -- this
    function only forwards the cart contents and chosen address.
    """
    if settings.API_USE_MOCKS:
        return _mock_create_order(items, shipping_address_id, notes)

    payload = {"items": items, "shipping_address_id": shipping_address_id}
    if notes:
        payload["notes"] = notes
    return api_client.post("/api/v1/orders", token=token, json=payload)


def _mock_create_order(items: list[dict], shipping_address_id: str, notes: str | None) -> dict:
    """Builds a contract-shaped order from the mock catalog and appends it to
    mock_data.MOCK_ORDERS so subsequent get_order()/list_orders() calls (the
    checkout redirect, the order detail page) can find it -- mirroring how
    the real backend persists what POST /orders creates.
    """
    line_items = []
    subtotal = Decimal("0")
    for entry in items:
        product = next((p for p in mock_data.MOCK_PRODUCTS if p["id"] == entry["product_id"]), None)
        if product is None:
            raise ApiConflictError(f"Producto {entry['product_id']} no disponible.", status_code=409)
        unit_price = Decimal(product["price"])
        quantity = entry["quantity"]
        line_total = unit_price * quantity
        subtotal += line_total
        line_items.append(
            {
                "id": str(uuid.uuid4()),
                "product_id": product["id"],
                "product_name": product["name"],
                "quantity": quantity,
                "unit_price": str(unit_price),
                "line_total": str(line_total),
            }
        )

    next_seq = len(mock_data.MOCK_ORDERS) + 1
    shipping_address = next(
        (a for a in mock_data.MOCK_ADDRESSES if a["id"] == shipping_address_id), None
    )
    order = {
        "id": str(uuid.uuid4()),
        "order_number": f"ORD-MOCK{next_seq:04d}",
        "customer_id": mock_data.MOCK_USER["id"],
        "status": "pending",
        "subtotal": str(subtotal),
        "tax_amount": "0.00",
        "shipping_amount": "0.00",
        "total_amount": str(subtotal),
        "shipping_address_id": shipping_address_id,
        "shipping_address": shipping_address,
        "notes": notes,
        "items": line_items,
        "created_at": "2026-09-08T00:00:00Z",
        "updated_at": "2026-09-08T00:00:00Z",
    }
    mock_data.MOCK_ORDERS.append(order)
    return order


def cancel_order(token: str, order_id: str) -> dict:
    if settings.API_USE_MOCKS:
        order = next((o for o in mock_data.MOCK_ORDERS if o["id"] == str(order_id)), None)
        if order is None:
            raise ApiConflictError("Pedido no encontrado.", status_code=404)
        order["status"] = "cancelled"
        return order
    return api_client.post(f"/api/v1/orders/{order_id}/cancel", token=token)


def update_status(token: str, order_id: str, status: str) -> dict:
    """Staff only: manual correction, restricted to ORDER_TRANSITIONS (409
    otherwise). /payments and /shipments drive the normal flow. Cancelling or
    refunding releases reserved stock, writes a reversal ledger entry if the
    order was paid, and cancels an undispatched shipment -- all backend-side.
    """
    if settings.API_USE_MOCKS:
        order = next((o for o in mock_data.MOCK_ORDERS if o["id"] == str(order_id)), None)
        if order is None:
            raise ApiConflictError("Pedido no encontrado.", status_code=404)
        if status not in next_statuses(order["status"]):
            raise ApiConflictError("Invalid status transition.", status_code=409)
        order["status"] = status
        shipment = mock_data.MOCK_SHIPMENTS.get(str(order_id))
        if status in ("cancelled", "refunded") and shipment and shipment["status"] in ("pending", "preparing"):
            shipment["status"] = "cancelled"
        return order
    return api_client.patch(f"/api/v1/orders/{order_id}/status", token=token, json={"status": status})
