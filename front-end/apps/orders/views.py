from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.accounts.decorators import api_login_required
from services import auth as auth_service
from services import customers as customers_service
from services import orders as orders_service
from services import payments as payments_service
from services import shipments as shipments_service
from services.exceptions import ApiConflictError, ApiError


@api_login_required
def order_list(request):
    token = auth_service.get_access_token(request)
    result = orders_service.list_orders(token)
    return render(request, "orders/list.html", {"orders": result["items"]})


@api_login_required
def order_detail(request, order_id):
    token = auth_service.get_access_token(request)
    order = orders_service.get_order(token, str(order_id))
    if order is None:
        raise Http404("Pedido no encontrado")

    shipment = shipments_service.get_shipment_for_order(token, str(order_id))
    payments = payments_service.list_payments_for_order(token, str(order_id))
    cancellable = order["status"] in ("pending", "awaiting_payment")

    context = {"order": order, "shipment": shipment, "payments": payments, "cancellable": cancellable}
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
