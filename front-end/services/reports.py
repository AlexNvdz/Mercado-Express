"""
Admin dashboard statistics (apps/adminpanel). See
../API_CONTRACT.md#apiv1reports.

    GET /api/v1/reports/summary?top_products_limit=   staff
    GET /api/v1/inventory?low_stock=true              staff, paginated
    GET /api/v1/orders?page=1&page_size=8             staff sees every order

Every number comes from the backend: revenue is summed server-side from the
`Sale` ledger (not `Order.total_amount`), order counts and top products are
computed there too. A paid order later cancelled or refunded gets a negative
(reversal) ledger entry, so `net_revenue = gross_revenue - refunded_amount`
(`refunded_amount` is positive); `sale_count` counts sales only,
`reversal_count` the reversals. This module only reshapes the three
responses for the template and resolves product names for the low-stock rows
(InventoryOut has no name).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.conf import settings

from . import inventory as inventory_service
from . import mock_data
from . import orders as orders_service
from . import products as products_service
from .api_client import api_client
from .orders import ORDER_STATUSES

RECENT_ORDERS_LIMIT = 8
TOP_PRODUCTS_LIMIT = 6
# One page of low-stock rows is enough for the dashboard alert; the card
# shows the backend's `total`, the table only the LOW_STOCK_SHOWN lowest.
LOW_STOCK_PAGE_SIZE = inventory_service.MAX_PAGE_SIZE
LOW_STOCK_SHOWN = 10


def _to_decimal(value) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return Decimal("0")


def get_summary(token: str, *, top_products_limit: int = TOP_PRODUCTS_LIMIT) -> dict:
    """Staff only: GET /reports/summary, as returned by the backend."""
    if settings.API_USE_MOCKS:
        summary = mock_data.MOCK_REPORT_SUMMARY
        return {**summary, "top_products": summary["top_products"][:top_products_limit]}
    return api_client.get(
        "/api/v1/reports/summary", token=token, params={"top_products_limit": top_products_limit}
    )


def _low_stock_rows(token: str) -> tuple[list[dict], int]:
    page = inventory_service.list_inventory(token, low_stock=True, page_size=LOW_STOCK_PAGE_SIZE)
    rows = sorted(page["items"], key=lambda row: row["quantity_available"])[:LOW_STOCK_SHOWN]
    enriched = []
    for availability in rows:
        product_id = availability["product_id"]
        product = products_service.get_product(product_id)
        name = product["name"] if product else f"Producto no disponible ({product_id[:8]})"
        enriched.append({"product_id": product_id, "name": name, "availability": availability})
    return enriched, page["total"]


def get_dashboard_stats(token: str) -> dict:
    summary = get_summary(token)

    counts = {row["status"]: row["count"] for row in summary["orders_by_status"]}
    # Ordered by the lifecycle (see ORDER_STATUSES) so the breakdown reads
    # top-to-bottom like a funnel; zero rows are hidden.
    orders_by_status = {status: counts[status] for status in ORDER_STATUSES if counts.get(status)}

    low_stock, low_stock_count = _low_stock_rows(token)
    recent_orders = orders_service.list_orders(token, page=1, page_size=RECENT_ORDERS_LIMIT)["items"]

    return {
        "net_revenue": _to_decimal(summary["net_revenue"]),
        "gross_revenue": _to_decimal(summary["gross_revenue"]),
        "refunded_amount": _to_decimal(summary["refunded_amount"]),
        "sale_count": summary["sale_count"],
        "reversal_count": summary["reversal_count"],
        "total_products": summary["product_count"],
        "total_customers": summary["customer_count"],
        "total_orders": sum(counts.values()),
        "orders_by_status": orders_by_status,
        "recent_orders": recent_orders[:RECENT_ORDERS_LIMIT],
        "top_products": summary["top_products"],
        "low_stock": low_stock,
        "low_stock_count": low_stock_count,
    }
