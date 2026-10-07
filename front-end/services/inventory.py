"""
Stock availability. See ../API_CONTRACT.md#apiv1inventory.

    GET  /api/v1/inventory?low_stock=&include_inactive=&page=&page_size=   staff, paginated
    GET  /api/v1/inventory/{product_id}
    GET  /api/v1/inventory/{product_id}/history?page=&page_size=   staff, newest first
    POST /api/v1/inventory/{product_id}/adjust   staff, {"delta": int, "reason": str|None}
    PUT  /api/v1/inventory/{product_id}          staff, {"quantity_on_hand": int, "reorder_level": int|None, "reason": str|None}

Stock is a separate resource from the product itself (single stock pool per
product on the backend); this module is the only place that reads/writes it.
`delta` is signed: positive restocks, negative removes (shrinkage,
correction) -- confirmed against backend-api/app/schemas/inventory.py.
Both staff writes record an entry in the product's history (who, before/
after, `reason`); order reservations/releases/fulfillments do not -- those
are traced through the order's status history instead.
"""

from __future__ import annotations

import uuid

from django.conf import settings

from . import mock_data
from .api_client import api_client
from .exceptions import ApiNotFoundError

# Backend's MAX_PAGE_SIZE for paginated lists (422 above it).
MAX_PAGE_SIZE = 100

# Mirrors backend-api's inventory history `kind` values. Spanish display
# labels, never render the raw value.
INVENTORY_CHANGE_KIND_LABELS = {
    "adjust": "Ajuste de stock",
    "set_levels": "Niveles fijados",
}


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


def list_inventory(
    token: str, *, low_stock: bool = False, include_inactive: bool = False, page: int = 1, page_size: int = 20
) -> dict:
    """Staff only: paginated inventory rows, `{items, total, page, page_size,
    pages}`. Each item has the same shape as get_availability() -- product_id
    only, no product name (resolve it with services.products.get_product).
    `low_stock=True` keeps rows where quantity_available <= reorder_level.
    Rows of inactive products are left out unless `include_inactive`, so the
    low-stock alert ignores discontinued products. The backend orders rows by
    updated_at desc, not by stock level.
    """
    if settings.API_USE_MOCKS:
        active_ids = {p["id"] for p in mock_data.MOCK_PRODUCTS if p.get("is_active", True)}
        items = [
            get_availability(product_id)
            for product_id in mock_data.MOCK_INVENTORY
            if include_inactive or product_id in active_ids
        ]
        if low_stock:
            items = [row for row in items if row["quantity_available"] <= row["reorder_level"]]
        return {"items": items, "total": len(items), "page": 1, "page_size": len(items) or 1, "pages": 1}

    params: dict = {"page": page, "page_size": page_size}
    if low_stock:
        params["low_stock"] = "true"
    if include_inactive:
        params["include_inactive"] = "true"
    return api_client.get("/api/v1/inventory", token=token, params=params)


def availability_by_product(token: str, product_ids: list[str]) -> dict[str, dict]:
    """Staff only: inventory rows for `product_ids` (active or not), keyed by
    product_id.

    GET /inventory has no product filter, so this pages through it at the
    backend's max page_size and stops as soon as every requested product is
    found (or the rows run out). Products with no inventory row are simply
    missing from the result.
    """
    wanted = {str(product_id) for product_id in product_ids}
    found: dict[str, dict] = {}
    page = 1
    while wanted - found.keys():
        result = list_inventory(token, include_inactive=True, page=page, page_size=MAX_PAGE_SIZE)
        for row in result["items"]:
            if row["product_id"] in wanted:
                found[row["product_id"]] = row
        if page >= result["pages"]:
            break
        page += 1
    return found


def adjust_stock(token: str, product_id: str, delta: int, reason: str | None = None) -> dict:
    """Add (delta > 0) or remove (delta < 0) stock -- restock/shrinkage/correction."""
    if settings.API_USE_MOCKS:
        record = mock_data.MOCK_INVENTORY.setdefault(
            str(product_id), {"quantity_on_hand": 0, "quantity_reserved": 0, "reorder_level": 0}
        )
        before = dict(record)
        record["quantity_on_hand"] = max(0, record["quantity_on_hand"] + delta)
        _mock_record_history(product_id, "adjust", before, record, reason)
        return get_availability(product_id)

    payload = {"delta": delta, "reason": reason}
    return api_client.post(f"/api/v1/inventory/{product_id}/adjust", token=token, json=payload)


def set_levels(
    token: str,
    product_id: str,
    quantity_on_hand: int,
    reorder_level: int | None = None,
    reason: str | None = None,
) -> dict:
    """Set absolute on-hand/reorder levels (inventory count correction). 409
    if quantity_on_hand would drop below the reserved quantity.
    """
    if settings.API_USE_MOCKS:
        record = mock_data.MOCK_INVENTORY.setdefault(
            str(product_id), {"quantity_on_hand": 0, "quantity_reserved": 0, "reorder_level": 0}
        )
        before = dict(record)
        record["quantity_on_hand"] = quantity_on_hand
        if reorder_level is not None:
            record["reorder_level"] = reorder_level
        _mock_record_history(product_id, "set_levels", before, record, reason)
        return get_availability(product_id)

    payload = {"quantity_on_hand": quantity_on_hand, "reorder_level": reorder_level, "reason": reason}
    return api_client.put(f"/api/v1/inventory/{product_id}", token=token, json=payload)


def list_history(token: str, product_id: str, *, page: int = 1, page_size: int = 20) -> dict:
    """Staff only: the product's manual stock changes, newest first, as the
    standard paginated envelope. Each item: {id, product_id, kind,
    quantity_on_hand_before/after, quantity_delta, reorder_level_before/
    after, reason, actor: {id, email, full_name, role} | null, created_at}.
    """
    if settings.API_USE_MOCKS:
        items = mock_data.MOCK_INVENTORY_HISTORY.get(str(product_id), [])
        return {"items": items, "total": len(items), "page": 1, "page_size": len(items) or 1, "pages": 1}
    return api_client.get(
        f"/api/v1/inventory/{product_id}/history", token=token, params={"page": page, "page_size": page_size}
    )


def _mock_record_history(product_id: str, kind: str, before: dict, after: dict, reason: str | None) -> None:
    entries = mock_data.MOCK_INVENTORY_HISTORY.setdefault(str(product_id), [])
    entries.insert(
        0,
        {
            "id": str(uuid.uuid4()),
            "product_id": str(product_id),
            "kind": kind,
            "quantity_on_hand_before": before["quantity_on_hand"],
            "quantity_on_hand_after": after["quantity_on_hand"],
            "quantity_delta": after["quantity_on_hand"] - before["quantity_on_hand"],
            "reorder_level_before": before["reorder_level"],
            "reorder_level_after": after["reorder_level"],
            "reason": reason,
            "actor": mock_data.MOCK_STAFF_ACTOR,
            "created_at": "2026-10-07T12:00:00Z",
        },
    )
