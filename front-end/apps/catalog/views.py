from django.http import Http404
from django.shortcuts import render

from services import inventory, products


def product_list(request, category_id=None):
    search = request.GET.get("q", "").strip()
    result = products.list_products(
        category_id=str(category_id) if category_id else None, search=search or None
    )
    categories = products.list_categories()["items"]
    active_category = next((c for c in categories if c["id"] == str(category_id)), None)

    context = {
        "products": result["items"],
        "total": result["total"],
        "categories": categories,
        "active_category": active_category,
        "search": search,
    }
    return render(request, "catalog/list.html", context)


def product_detail(request, product_id):
    product = products.get_product(str(product_id))
    if product is None:
        raise Http404("Producto no encontrado")

    category = products.get_category(product["category_id"])
    availability = inventory.get_availability(product["id"])

    context = {"product": product, "category": category, "availability": availability}
    return render(request, "catalog/detail.html", context)
