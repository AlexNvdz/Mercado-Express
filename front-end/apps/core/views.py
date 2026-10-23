from django.shortcuts import redirect, render

from services import auth as auth_service
from services import inventory, products
from services import orders as orders_service
from services.exceptions import ApiError

HOME_SECTIONS = 3
HOME_PER_SECTION = 4


def home(request):
    # Admin/employee accounts manage the store from the dashboard, not the
    # storefront -- see apps/adminpanel.
    if auth_service.is_staff(request):
        return redirect("adminpanel:home")

    categories = products.list_categories_with_products()
    sections = []
    for category in categories[:HOME_SECTIONS]:
        items = products.list_products(category_id=category["id"], page_size=HOME_PER_SECTION)["items"]
        # One stock read per product shown (at most HOME_SECTIONS x HOME_PER_SECTION):
        # the public inventory endpoint has no batch form.
        items = [{**p, "availability": inventory.get_availability(p["id"])} for p in items[:HOME_PER_SECTION]]
        # The title promises that what is shown is in stock: sold-out products
        # stay in the catalog (marked "Agotado"), not on the home.
        items = [p for p in items if p["availability"] and p["availability"]["quantity_available"] > 0]
        if items:
            sections.append({"category": category, "products": items})

    shown = [p for section in sections for p in section["products"]]
    in_stock = [p for p in shown if p.get("images")]
    context = {
        "sections": sections,
        "category_count": len(categories),
        "product_count": sum(c["active_product_count"] for c in categories),
        # The example order in the hero plays with a real product, labelled "Ejemplo".
        "example": in_stock[0] if in_stock else None,
        "ambient": [p["images"][0]["url"] for p in shown if p.get("images")][:3],
        "last_order": _last_order(request),
    }
    return render(request, "core/home.html", context)


def _last_order(request):
    """The customer's newest order, for "Repetir mi último pedido"; None for
    visitors or when the call fails (the home never breaks over it).
    """
    if not auth_service.is_authenticated(request):
        return None
    try:
        items = orders_service.list_orders(auth_service.get_access_token(request), page=1, page_size=1)["items"]
    except ApiError:
        return None
    return items[0] if items else None
