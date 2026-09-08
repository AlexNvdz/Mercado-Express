from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from services import products as products_service


def detail(request):
    context = {
        "items": list(request.cart),
        "total": request.cart.get_total(),
    }
    return render(request, "cart/detail.html", context)


@require_POST
def add(request, product_id):
    product = products_service.get_product(str(product_id))
    if product is None:
        messages.error(request, "Producto no encontrado.")
        return redirect("core:home")

    quantity = int(request.POST.get("quantity", 1))
    request.cart.add(str(product_id), quantity)
    messages.success(request, f"{product['name']} añadido al carrito.")
    return redirect(request.POST.get("next") or "cart:detail")


@require_POST
def update(request, product_id):
    quantity = int(request.POST.get("quantity", 1))
    request.cart.update(str(product_id), quantity)
    return redirect("cart:detail")


@require_POST
def remove(request, product_id):
    request.cart.remove(str(product_id))
    return redirect("cart:detail")
