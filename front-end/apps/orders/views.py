from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.accounts.decorators import api_login_required
from services import auth as auth_service
from services import customers as customers_service
from services import orders as orders_service
from services import payments as payments_service
from services import products as products_service
from services import shipments as shipments_service
from services.exceptions import ApiConflictError, ApiError


@api_login_required
def order_list(request):
    token = auth_service.get_access_token(request)
    result = orders_service.list_orders(token)
    orders = result["items"]

    status_filter = request.GET.get("status") or ""
    statuses = sorted({o["status"] for o in orders})
    if status_filter:
        orders = [o for o in orders if o["status"] == status_filter]

    context = {"orders": orders, "statuses": statuses, "status_filter": status_filter}
    return render(request, "orders/list.html", context)


TRACKER_STEPS = [
    ("pending", "Pedido creado"),
    ("paid", "Pago confirmado"),
    ("preparing", "Preparando"),
    ("shipped", "Enviado"),
    ("delivered", "Entregado"),
]


def _build_tracker(status: str) -> list[dict] | None:
    """Maps the order's lifecycle status (API_CONTRACT.md#apiv1orders) onto
    TRACKER_STEPS for the progress bar. Returns None for terminal states
    that fall outside the normal flow (cancelled/refunded).
    """
    if status in ("cancelled", "refunded"):
        return None

    # awaiting_payment sits at the same visual step as pending (still
    # "pedido creado" from the customer's point of view).
    effective = "pending" if status == "awaiting_payment" else status
    order_index = {key: i for i, (key, _label) in enumerate(TRACKER_STEPS)}
    current = order_index.get(effective, 0)

    steps = []
    for i, (key, label) in enumerate(TRACKER_STEPS):
        if i < current:
            state = "done"
        elif i == current:
            state = "current"
        else:
            state = "upcoming"
        steps.append({"key": key, "label": label, "state": state})
    return steps


def _enrich_items_with_product_names(items: list[dict]) -> list[dict]:
    """API_CONTRACT.md's order-item shape has no product name (only
    product_id/quantity/unit_price/line_total) -- confirmed against the real
    backend, not just the doc. Resolve it here so templates can show
    something better than a blank cell; falls back to the SKU/id if the
    product was since deleted.
    """
    cache: dict[str, dict | None] = {}
    enriched = []
    for item in items:
        product_id = item["product_id"]
        if product_id not in cache:
            cache[product_id] = products_service.get_product(product_id)
        product = cache[product_id]
        name = product["name"] if product else f"Producto no disponible ({product_id[:8]})"
        enriched.append({**item, "product_name": name})
    return enriched


@api_login_required
def order_detail(request, order_id):
    token = auth_service.get_access_token(request)
    order = orders_service.get_order(token, str(order_id))
    if order is None:
        raise Http404("Pedido no encontrado")

    order = {**order, "items": _enrich_items_with_product_names(order["items"])}
    shipment = shipments_service.get_shipment_for_order(token, str(order_id))
    payments = payments_service.list_payments_for_order(token, str(order_id))
    cancellable = order["status"] in ("pending", "awaiting_payment")

    context = {
        "order": order,
        "shipment": shipment,
        "payments": payments,
        "cancellable": cancellable,
        "tracker_steps": _build_tracker(order["status"]),
    }
    return render(request, "orders/detail.html", context)


@api_login_required
def order_cancel(request, order_id):
    if request.method == "POST":
        token = auth_service.get_access_token(request)
        try:
            orders_service.cancel_order(token, str(order_id))
        except ApiConflictError as exc:
            messages.error(request, exc.detail)
        except ApiError:
            messages.error(request, "No fue posible cancelar el pedido.")
        else:
            messages.success(request, "Pedido cancelado.")
    return redirect("orders:detail", order_id=order_id)


@api_login_required
def order_reorder(request, order_id):
    """Adds every item from a past order back into the cart ("repetir
    pedido"). Prices are re-fetched from services.products when the cart is
    rendered/checked out -- this never reuses the order's old unit_price.
    """
    if request.method == "POST":
        token = auth_service.get_access_token(request)
        order = orders_service.get_order(token, str(order_id))
        if order is None:
            raise Http404("Pedido no encontrado")

        added = 0
        for item in order["items"]:
            product = products_service.get_product(item["product_id"])
            if product is None:
                continue
            request.cart.add(item["product_id"], item["quantity"])
            added += 1

        if added:
            messages.success(request, "Productos añadidos al carrito.")
        else:
            messages.warning(request, "Ninguno de los productos de este pedido está disponible ahora.")
        return redirect("cart:detail")
    return redirect("orders:detail", order_id=order_id)


@api_login_required
def checkout(request):
    token = auth_service.get_access_token(request)
    addresses = customers_service.list_addresses(token)

    if len(request.cart) == 0:
        messages.error(request, "Tu carrito está vacío.")
        return redirect("cart:detail")

    if not addresses:
        messages.info(request, "Añade una dirección de envío para continuar.")
        return redirect(f"{reverse('dashboard:address_add')}?next={reverse('orders:checkout')}")

    if request.method != "POST":
        context = {
            "items": list(request.cart),
            "total": request.cart.get_total(),
            "addresses": addresses,
        }
        return render(request, "orders/checkout.html", context)

    shipping_address_id = request.POST.get("shipping_address_id")
    if not shipping_address_id:
        messages.error(request, "Selecciona una dirección de envío.")
        return redirect("orders:checkout")

    try:
        order = orders_service.create_order(
            token,
            request.cart.as_order_items(),
            shipping_address_id=shipping_address_id,
            notes=request.POST.get("notes") or None,
        )
    except ApiConflictError as exc:
        messages.error(request, exc.detail or "Uno o más productos ya no tienen stock suficiente.")
        return redirect("cart:detail")
    except ApiError:
        messages.error(request, "No fue posible crear el pedido. Intenta más tarde.")
        return redirect("cart:detail")

    # No real payment gateway on the backend yet -- this completes the order
    # immediately via the manual/placeholder gateway (see API_CONTRACT.md).
    try:
        payments_service.create_payment(token, order["id"], method="card")
    except ApiError:
        messages.warning(
            request, "El pedido se creó, pero el pago no se pudo confirmar automáticamente."
        )

    request.cart.clear()
    messages.success(request, "¡Pedido creado con éxito!")
    return redirect("orders:detail", order_id=order["id"])
