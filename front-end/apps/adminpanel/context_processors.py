from services import auth as auth_service
from services import inventory as inventory_service
from services import products as products_service
from services import reports as reports_service
from services.exceptions import ApiError

PANEL_PREFIXES = ("/panel/", "/catalogo/admin/")


def panel(request):
    """Rail counts and the staff role for panel pages only: totals from
    GET /reports/summary (cached 10 s by the backend), plus one-row reads of
    GET /categories and GET /inventory?low_stock=true for their totals. A
    failed call just hides the counts.
    """
    if not request.path.startswith(PANEL_PREFIXES) or not auth_service.is_staff(request):
        return {}
    context = {"panel_role": auth_service.get_role(request)}
    try:
        token = auth_service.get_access_token(request)
        summary = reports_service.get_summary(token)
        context["rail_counts"] = {
            "orders": sum(row["count"] for row in summary["orders_by_status"]),
            "customers": summary["customer_count"],
            "products": summary["product_count"],
            "categories": products_service.list_categories(page=1, page_size=1)["total"],
            "low_stock": inventory_service.list_inventory(token, low_stock=True, page_size=1)["total"],
        }
    except (ApiError, KeyError, TypeError):
        pass  # counts are a convenience: never break a panel page over them
    return context
