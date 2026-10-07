"""
Admin dashboard statistics (apps/adminpanel).

There is no dedicated aggregate/reporting endpoint on backend-api yet (see
API_CONTRACT.md's "Open items"). This module builds the dashboard's numbers
by composing the resource endpoints that already exist -- orders, products,
inventory, customers -- rather than duplicating business logic client-side:
every number here is a straight read or a sum of fields the backend already
computed (order totals, stock levels), never a re-derivation of things like
tax/shipping/stock-reservation math, which stay backend-owned.

Caveats, by design, until backend-api adds a real reports endpoint (see
API_CONTRACT.md and the instructions left for backend-api):
  - Orders are paged in from `GET /orders` up to MAX_ORDER_PAGES pages of
    MAX_PAGE_SIZE each; on a store with more orders than that, totals below
    are a recent-window approximation, not the full history. `orders_capped`
    tells the template whether this happened.
  - `revenue_total` sums `Order.total_amount` for orders that reached a
    paid-or-later status. It is a proxy for real revenue -- the backend's
    `Sale` table (see CLAUDE.md: the immutable financial ledger) is the
    actual source of truth and should back this once exposed via the API.
  - `low_stock` only inspects the first MAX_LOW_STOCK_PRODUCTS products
    (one GET /inventory/{id} call each -- there is no batch/list endpoint).
"""

from __future__ import annotations

from collections import Counter
from decimal import Decimal, InvalidOperation

from . import customers as customers_service
from . import inventory as inventory_service
from . import orders as orders_service
from . import products as products_service
from .orders import ORDER_STATUSES

MAX_ORDER_PAGES = 5
MAX_PAGE_SIZE = 100
MAX_LOW_STOCK_PRODUCTS = 60
RECENT_ORDERS_LIMIT = 8
TOP_PRODUCTS_LIMIT = 6

# Statuses that represent money actually collected (payment completed).
REVENUE_STATUSES = {"paid", "preparing", "shipped", "delivered"}
# Statuses excluded when counting units sold for the "top products" list --
# an order that never got paid never really "sold" anything.
UNSOLD_STATUSES = {"pending", "cancelled"}


def _to_decimal(value) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return Decimal("0")


def _collect_orders(token: str) -> tuple[list[dict], bool]:
    """Pages through GET /orders (staff sees every order) up to
    MAX_ORDER_PAGES pages. Returns (orders, capped) -- capped is True if
    there were more pages than we fetched.
    """
    orders: list[dict] = []
    page = 1
    total_pages = 1
    while page <= MAX_ORDER_PAGES:
        result = orders_service.list_orders(token, page=page, page_size=MAX_PAGE_SIZE)
        orders.extend(result["items"])
        total_pages = result.get("pages") or 1
        if page >= total_pages:
            break
        page += 1
    return orders, total_pages > MAX_ORDER_PAGES


def _top_products(orders: list[dict], products_by_id: dict[str, dict], limit: int) -> list[dict]:
    quantity_sold: Counter[str] = Counter()
    for order in orders:
        if order["status"] in UNSOLD_STATUSES:
            continue
        for item in order.get("items", []):
            quantity_sold[item["product_id"]] += item["quantity"]

    ranked = []
    for product_id, quantity in quantity_sold.most_common(limit):
        product = products_by_id.get(product_id)
        ranked.append(
            {
                "product_id": product_id,
                "name": product["name"] if product else f"Producto no disponible ({product_id[:8]})",
                "quantity_sold": quantity,
            }
        )
    return ranked


def get_dashboard_stats(token: str) -> dict:
    products_page = products_service.list_products(page=1, page_size=MAX_PAGE_SIZE)
    products = products_page["items"]
    products_by_id = {p["id"]: p for p in products}

    customers_page = customers_service.list_customers(token, page=1, page_size=1)

    orders, orders_capped = _collect_orders(token)
    status_counts = Counter(o["status"] for o in orders)
    # Ordered by the lifecycle (see ORDER_STATUSES), not by first appearance,
    # so the breakdown on the dashboard reads top-to-bottom like a funnel.
    orders_by_status = {status: status_counts[status] for status in ORDER_STATUSES if status_counts[status]}
    revenue_total = sum(
        (_to_decimal(o["total_amount"]) for o in orders if o["status"] in REVENUE_STATUSES),
        Decimal("0"),
    )
    recent_orders = sorted(orders, key=lambda o: o["created_at"], reverse=True)[:RECENT_ORDERS_LIMIT]
    top_products = _top_products(orders, products_by_id, TOP_PRODUCTS_LIMIT)

    low_stock = []
    for product in products[:MAX_LOW_STOCK_PRODUCTS]:
        availability = inventory_service.get_availability(product["id"])
        if availability and availability["quantity_available"] <= availability.get("reorder_level", 0):
            low_stock.append({"product": product, "availability": availability})
    low_stock.sort(key=lambda row: row["availability"]["quantity_available"])

    return {
        "total_products": products_page["total"],
        "total_customers": customers_page["total"],
        "total_orders": len(orders),
        "orders_capped": orders_capped,
        "orders_by_status": orders_by_status,
        "revenue_total": revenue_total,
        "recent_orders": recent_orders,
        "top_products": top_products,
        "low_stock": low_stock,
        "low_stock_count": len(low_stock),
    }
