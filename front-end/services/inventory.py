"""
Stock availability. See ../API_CONTRACT.md#apiv1inventory.

    GET  /api/v1/inventory?low_stock=&page=&page_size=   staff, paginated
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

# Backend's MAX_PAGE_SIZE for paginated lists (422 above it).
MAX_PAGE_SIZE = 100


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


def list_inventory(token: str, *, low_stock: bool = False, page: int = 1, page_size: int = 20) -> dict:
    """Staff only: paginated inventory rows, `{items, total, page, page_size,
    pages}`. Each item has the same shape as get_availability() -- product_id
    only, no product name (resolve it with services.products.get_product).
    `low_stock=True` keeps rows where quantity_available <= reorder_level.
    The backend orders rows by updated_at desc, not by stock level.
    """
    if settings.API_USE_MOCKS:
        items = [get_availability(product_id) for product_id in mock_data.MOCK_INVENTORY]
        if low_stock:
            items = [row for row in items if row["quantity_available"] <= row["reorder_level"]]
        return {"items": items, "total": len(items), "page": 1, "page_size": len(items) or 1, "pages": 1}

    params: dict = {"page": page, "page_size": page_size}
    if low_stock:
        params["low_stock"] = "true"
    return api_client.get("/api/v1/inventory", token=token, params=params)


def availability_by_product(token: str, product_ids: list[str]) -> dict[str, dict]:
    """Staff only: inventory rows for `product_ids`, keyed by product_id.

    GET /inventory has no product filter, so this pages through it at the
    backend's max page_size and stops as soon as every requested product is
    found (or the rows run out). Products with no inventory row are simply
    missing from the result.
    """
    wanted = {str(product_id) for product_id in product_ids}
    found: dict[str, dict] = {}
    page = 1
    while wanted - found.keys():
        result = list_inventory(token, page=page, page_size=MAX_PAGE_SIZE)
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
