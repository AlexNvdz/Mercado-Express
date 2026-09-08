from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from services import inventory, products


def product_list(request, category_id=None):
    search = request.GET.get("q", "").strip()
    try:
        page = max(1, int(request.GET.get("page", 1)))
    except ValueError:
        page = 1

    result = products.list_products(
        category_id=str(category_id) if category_id else None,
        search=search or None,
        page=page,
    )
    categories = products.list_categories()["items"]
    active_category = next((c for c in categories if c["id"] == str(category_id)), None)

    context = {
        "products": result["items"],
        "total": result["total"],
        "page": result["page"],
        "pages": result["pages"],
        "has_previous": result["page"] > 1,
        "has_next": result["page"] < result["pages"],
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


@require_POST
def wishlist_toggle(request, product_id):
    product = products.get_product(str(product_id))
    if product is None:
        messages.error(request, "Producto no encontrado.")
        return redirect("core:home")

    favorited = request.wishlist.toggle(str(product_id))
    if favorited:
        messages.success(request, f"{product['name']} añadido a favoritos.")
    else:
        messages.info(request, f"{product['name']} quitado de favoritos.")
    return redirect(request.POST.get("next") or "catalog:wishlist")


def wishlist_view(request):
    return render(request, "catalog/wishlist.html", {"products": list(request.wishlist)})
