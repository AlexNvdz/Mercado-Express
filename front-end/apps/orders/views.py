import uuid

from django.contrib import messages
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from apps.accounts.decorators import api_login_required
from apps.core.templatetags.money import api_date
from services import auth as auth_service
from services import customers as customers_service
from services import orders as orders_service
from services import payments as payments_service
from services import products as products_service
from services import shipments as shipments_service
from services import support as support_service
from services.exceptions import (
    ApiAuthenticationError,
    ApiConflictError,
    ApiError,
    ApiTimeoutError,
    ApiValidationError,
)


@api_login_required
def order_list(request):
    token = auth_service.get_access_token(request)
    try:
        page = max(1, int(request.GET.get("page", 1)))
    except ValueError:
        page = 1
    status_filter = request.GET.get("status") or ""
    if status_filter not in orders_service.ORDER_STATUSES:
        status_filter = ""
    result = orders_service.list_orders(token, page=page, page_size=10, status=status_filter or None)

    context = {
        "orders": result["items"],
        "statuses": orders_service.ORDER_STATUSES,
        "status_filter": status_filter,
        "page": result["page"],
        "pages": result["pages"],
    }
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

    order_index = {key: i for i, (key, _label) in enumerate(TRACKER_STEPS)}
    current = order_index.get(status, 0)

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
        if item.get("product_name"):  # asked of backend-api: no per-line lookup then
            enriched.append(item)
            continue
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
    cancellable = order["status"] == "pending"

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
        except (ApiConflictError, ApiValidationError):
            # 422 = the order is no longer `pending`. The backend's `detail`
            # is English, for developers -- never shown to the customer.
            messages.error(request, "Este pedido ya no se puede cancelar.")
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

    unavailable = [item["product"]["name"] for item in request.cart if not products_service.is_purchasable(item["product"])]
    if unavailable:
        messages.error(
            request,
            f"Ya no están disponibles: {', '.join(unavailable)}. Quítalos del carrito para continuar.",
        )
        return redirect("cart:detail")

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

    # No real payment gateway on the backend yet: the order is paid right away
    # via the manual gateway, in the same transaction (see API_CONTRACT.md).
    try:
        order = orders_service.checkout(
            token,
            request.cart.as_order_items(),
            shipping_address_id=shipping_address_id,
            notes=request.POST.get("notes") or None,
            method="card",
        )
    except ApiConflictError:
        # 409 = insufficient stock. The backend's `detail` is English and
        # names the product by UUID, so it is not shown to the customer.
        messages.error(
            request, "Uno o más productos ya no tienen stock suficiente. Revisa las cantidades de tu carrito."
        )
        return redirect("cart:detail")
    except ApiError:
        messages.error(request, "No fue posible crear el pedido. Intenta más tarde.")
        return redirect("cart:detail")

    request.cart.clear()
    messages.success(request, "¡Pedido creado con éxito!")
    return redirect("orders:detail", order_id=order["id"])


# --- Refund claims (floating widget, templates/partials/support_chat.html) ---
# JSON for the widget's fetch(): a login redirect would hand it an HTML page.
CLAIM_MESSAGE_MIN = 10  # backend's min_length, counted on the customer's own words
CLAIM_MESSAGE_MAX = 1900  # backend allows 2000, the "Pedido <uuid>: " prefix takes 45
_SESSION_EXPIRED = "Tu sesión expiró. Inicia sesión de nuevo."


def _claim_error(message: str, status: int) -> JsonResponse:
    return JsonResponse({"error": message}, status=status)


@require_GET
def claim_orders(request):
    """The customer's delivered orders, the only ones a claim can refund."""
    token = auth_service.get_access_token(request)
    if not token:
        return _claim_error(_SESSION_EXPIRED, 401)
    try:
        page = orders_service.list_orders(token, status="delivered", page_size=20)
    except ApiAuthenticationError:
        return _claim_error(_SESSION_EXPIRED, 401)
    except ApiError:
        return _claim_error("No pudimos cargar tus pedidos.", 502)
    orders = [
        {"id": o["id"], "order_number": o["order_number"], "created": api_date(o["created_at"])}
        for o in page["items"]
    ]
    return JsonResponse({"orders": orders})


@require_POST
def claim_submit(request):
    token = auth_service.get_access_token(request)
    if not token:
        return _claim_error(_SESSION_EXPIRED, 401)
    try:
        order_id = str(uuid.UUID(request.POST.get("order_id", "")))
    except ValueError:
        return _claim_error("Elige el pedido de tu reclamo.", 400)
    mensaje = request.POST.get("mensaje", "").strip()
    if not CLAIM_MESSAGE_MIN <= len(mensaje) <= CLAIM_MESSAGE_MAX:
        return _claim_error(f"Escribe entre {CLAIM_MESSAGE_MIN} y {CLAIM_MESSAGE_MAX} caracteres.", 400)

    try:
        result = support_service.procesar_reclamo(token, order_id, mensaje)
    except ApiAuthenticationError:
        return _claim_error(_SESSION_EXPIRED, 401)
    except ApiTimeoutError:
        return _claim_error("El asistente tardó demasiado. Intenta de nuevo.", 504)
    except ApiError:
        return _claim_error("No pudimos procesar tu reclamo. Intenta de nuevo.", 502)

    status = result.get("order_status")
    return JsonResponse({
        "decision": result["decision"],
        "motivo": result["motivo"],
        "order_status_label": orders_service.ORDER_STATUS_LABELS.get(status, status) if status else None,
        "order_url": reverse("orders:detail", kwargs={"order_id": result["order_id"]}) if result.get("order_id") else None,
    })
