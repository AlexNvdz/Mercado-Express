"""
Staff-only admin dashboard: store-wide stats plus management screens for
everything that has no other frontend UI yet (categories, inventory, order
status/shipments, customers). Product create/edit/delete/images already has
its own UI at apps/catalog (catalog:admin_*) -- linked from here, not
duplicated.

Every view is @api_staff_required (see apps/accounts/decorators.py) and
talks to backend-api only through services/*.py, per CLAUDE.md.
"""

from datetime import date

from django.contrib import messages
from django.http import Http404, QueryDict
from django.utils.dateparse import parse_datetime
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.accounts.decorators import api_staff_required
from apps.core.templatetags.money import duration_label
from apps.catalog.views import product_filters
from services import auth as auth_service
from services import customers as customers_service
from services import inventory as inventory_service
from services import orders as orders_service
from services import products as products_service
from services import reports as reports_service
from services import shipments as shipments_service
from services.exceptions import ApiConflictError, ApiError, ApiNotFoundError, ApiValidationError

from .forms import (
    CategoryForm,
    InventoryAdjustForm,
    OrderStatusForm,
    ReorderLevelForm,
    ShipmentCreateForm,
    ShipmentUpdateForm,
)


def _enrich_items_with_product_names(items: list[dict]) -> list[dict]:
    """Order items only carry product_id/quantity/unit_price/line_total (see
    API_CONTRACT.md) -- resolve names for display, same approach as
    apps/orders/views.py:_enrich_items_with_product_names.
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


# --- Dashboard overview ------------------------------------------------


@api_staff_required
def home(request):
    token = auth_service.get_access_token(request)
    stats = reports_service.get_dashboard_stats(token)
    return render(request, "adminpanel/home.html", {"stats": stats, "active_nav": "home"})


# --- Orders (status overrides + shipment lifecycle) ---------------------


def _iso_day(value: str | None) -> str | None:
    """A YYYY-MM-DD day from the querystring, or None if missing or malformed
    (sent as-is the backend would 422).
    """
    try:
        return date.fromisoformat(value).isoformat() if value else None
    except ValueError:
        return None


@api_staff_required
def orders_list(request):
    token = auth_service.get_access_token(request)
    try:
        page = max(1, int(request.GET.get("page", 1)))
    except ValueError:
        page = 1

    # Unknown values are ignored rather than sent (the backend would 422).
    status_filter = request.GET.get("status") or ""
    if status_filter not in orders_service.ORDER_STATUSES:
        status_filter = ""

    search = request.GET.get("q", "").strip()[:100]
    created_from = _iso_day(request.GET.get("desde"))
    created_to = _iso_day(request.GET.get("hasta"))
    result = orders_service.list_orders(
        token,
        page=page,
        page_size=20,
        status=status_filter or None,
        search=search or None,
        created_from=created_from,
        created_to=created_to,
    )

    context = {
        "orders": result["items"],
        "total": result["total"],
        "statuses": orders_service.ORDER_STATUSES,
        "status_filter": status_filter,
        "search": search,
        "created_from": created_from or "",
        "created_to": created_to or "",
        "page": result["page"],
        "pages": result["pages"],
        "active_nav": "orders",
    }
    return render(request, "adminpanel/orders_list.html", context)


SEARCH_PER_GROUP = 6


def _with_elapsed(history: list[dict]) -> list[dict]:
    """Adds `elapsed` to each status change: the real time since the previous
    one ("2 h 15 min"), so slow steps stand out in the history.
    """
    previous = None
    annotated = []
    for entry in history:
        current = parse_datetime(entry["created_at"])
        elapsed = duration_label((current - previous).total_seconds()) if previous and current else ""
        annotated.append({**entry, "elapsed": elapsed})
        previous = current or previous
    return annotated


@api_staff_required
def search(request):
    """The top bar's search: orders, customers and products matching `q`, a
    few of each, with links to the full filtered lists.
    """
    token = auth_service.get_access_token(request)
    query = request.GET.get("q", "").strip()[:100]
    groups = []
    if query:
        orders = orders_service.list_orders(token, page=1, page_size=SEARCH_PER_GROUP, search=query)
        customers = customers_service.list_customers(token, page=1, page_size=SEARCH_PER_GROUP, search=query)
        products = products_service.list_products(
            search=query, page=1, page_size=SEARCH_PER_GROUP, include_inactive=True, token=token
        )
        groups = [
            {"kind": "orders", "label": "Pedidos", "items": orders["items"][:SEARCH_PER_GROUP], "total": orders["total"],
             "url": reverse("adminpanel:orders_list")},
            {"kind": "customers", "label": "Clientes", "items": customers["items"][:SEARCH_PER_GROUP], "total": customers["total"],
             "url": reverse("adminpanel:customers_list")},
            {"kind": "products", "label": "Productos", "items": products["items"][:SEARCH_PER_GROUP], "total": products["total"],
             "url": reverse("catalog:admin_list")},
        ]
    context = {
        "global_query": query,
        "groups": groups,
        "found": sum(group["total"] for group in groups),
        "active_nav": "",
    }
    return render(request, "adminpanel/search.html", context)


@api_staff_required
def order_detail(request, order_id):
    token = auth_service.get_access_token(request)
    order = orders_service.get_order(token, str(order_id))
    if order is None:
        raise Http404("Pedido no encontrado")

    order = {**order, "items": _enrich_items_with_product_names(order["items"])}
    customer = customers_service.get_customer(token, order["customer_id"])
    shipment = shipments_service.get_shipment_for_order(token, str(order_id))
    can_edit_shipment = shipment is not None and shipments_service.is_editable(shipment)
    try:
        status_history = _with_elapsed(orders_service.get_status_history(token, str(order_id)))
    except ApiError:
        status_history = None  # the template says it couldn't be loaded
    shipment_update_form = None
    if can_edit_shipment:
        shipment_update_form = ShipmentUpdateForm(
            initial={"carrier": shipment["carrier"], "tracking_number": shipment["tracking_number"]}
        )

    context = {
        "order": order,
        "customer": customer,
        "shipment": shipment,
        "status_form": OrderStatusForm(current_status=order["status"]),
        "next_statuses": orders_service.next_statuses(order["status"]),
        "shipment_form": ShipmentCreateForm(),
        "can_create_shipment": shipment is None and shipments_service.can_create_shipment(order["status"]),
        "can_edit_shipment": can_edit_shipment,
        "shipment_update_form": shipment_update_form,
        "can_ship": shipment is not None and shipment["status"] == "preparing" and order["status"] == "preparing",
        "can_deliver": shipment is not None and shipment["status"] == "in_transit",
        "status_history": status_history,
        "active_nav": "orders",
    }
    return render(request, "adminpanel/order_detail.html", context)


@api_staff_required
@require_POST
def order_status_update(request, order_id):
    token = auth_service.get_access_token(request)
    order = orders_service.get_order(token, str(order_id))
    if order is None:
        raise Http404("Pedido no encontrado")

    form = OrderStatusForm(request.POST, current_status=order["status"])
    if form.is_valid():
        try:
            orders_service.update_status(token, str(order_id), form.cleaned_data["status"])
        except ApiConflictError:
            messages.error(request, "El pedido no puede pasar a ese estado desde su estado actual.")
        except ApiError:
            messages.error(request, "No fue posible actualizar el estado del pedido.")
        else:
            messages.success(request, "Estado del pedido actualizado.")
    return redirect("adminpanel:order_detail", order_id=order_id)


@api_staff_required
@require_POST
def shipment_create(request, order_id):
    token = auth_service.get_access_token(request)
    order = orders_service.get_order(token, str(order_id))
    if order is None:
        raise Http404("Pedido no encontrado")
    if not order.get("shipping_address_id"):
        messages.error(request, "Este pedido no tiene una dirección de envío asociada.")
        return redirect("adminpanel:order_detail", order_id=order_id)

    form = ShipmentCreateForm(request.POST)
    if form.is_valid():
        try:
            shipments_service.create_shipment(
                token, str(order_id), order["shipping_address_id"], **form.to_api_kwargs()
            )
        except ApiConflictError:
            messages.error(
                request, "No se pudo crear el envío: el pedido debe estar pagado o en preparación y sin envío."
            )
        except ApiValidationError:
            messages.error(request, "Revisa la transportadora y el número de guía.")
        except ApiError:
            messages.error(request, "No fue posible crear el envío.")
        else:
            messages.success(request, "Envío creado.")
    else:
        messages.error(request, "Revisa la transportadora y el número de guía.")
    return redirect("adminpanel:order_detail", order_id=order_id)


@api_staff_required
@require_POST
def shipment_update(request, order_id):
    token = auth_service.get_access_token(request)
    shipment = shipments_service.get_shipment_for_order(token, str(order_id))
    if shipment is None:
        raise Http404("Envío no encontrado")

    form = ShipmentUpdateForm(request.POST)
    if form.is_valid():
        try:
            shipments_service.update_shipment(token, shipment["id"], str(order_id), **form.to_api_kwargs())
        except ApiConflictError:
            messages.error(request, "El envío ya fue despachado o cancelado: no se pueden cambiar sus datos.")
        except ApiValidationError:
            messages.error(request, "Revisa la transportadora y el número de guía.")
        except ApiError:
            messages.error(request, "No fue posible actualizar el envío.")
        else:
            messages.success(request, "Datos del envío actualizados.")
    else:
        messages.error(request, "Revisa la transportadora y el número de guía.")
    return redirect("adminpanel:order_detail", order_id=order_id)


@api_staff_required
@require_POST
def shipment_ship(request, order_id):
    token = auth_service.get_access_token(request)
    shipment = shipments_service.get_shipment_for_order(token, str(order_id))
    if shipment is None:
        raise Http404("Envío no encontrado")
    try:
        shipments_service.ship_shipment(token, shipment["id"], str(order_id))
    except ApiConflictError:
        messages.error(request, "Solo se puede despachar un envío en preparación de un pedido en preparación.")
    except ApiError:
        messages.error(request, "No fue posible marcar el envío como despachado.")
    else:
        messages.success(request, "Envío despachado.")
    return redirect("adminpanel:order_detail", order_id=order_id)


@api_staff_required
@require_POST
def shipment_deliver(request, order_id):
    token = auth_service.get_access_token(request)
    shipment = shipments_service.get_shipment_for_order(token, str(order_id))
    if shipment is None:
        raise Http404("Envío no encontrado")
    try:
        shipments_service.deliver_shipment(token, shipment["id"], str(order_id))
    except ApiConflictError:
        messages.error(request, "Solo se puede marcar como entregado un envío en camino.")
    except ApiError:
        messages.error(request, "No fue posible marcar el envío como entregado.")
    else:
        messages.success(request, "Envío entregado.")
    return redirect("adminpanel:order_detail", order_id=order_id)


# --- Categories -----------------------------------------------------------


@api_staff_required
def categories_list(request):
    categories = products_service.list_all_categories()
    return render(
        request, "adminpanel/categories_list.html", {"categories": categories, "active_nav": "categories"}
    )


@api_staff_required
def category_create(request):
    token = auth_service.get_access_token(request)
    categories = products_service.list_all_categories()
    form = CategoryForm(request.POST or None, categories=categories)

    if request.method == "POST" and form.is_valid():
        try:
            products_service.create_category(token, form.to_api_payload())
        except ApiConflictError:
            form.add_error("name", "Ya existe una categoría con ese nombre.")
        except ApiValidationError:
            form.add_error(None, "Revisa los datos de la categoría.")
        except ApiError:
            form.add_error(None, "No fue posible crear la categoría.")
        else:
            messages.success(request, "Categoría creada.")
            return redirect("adminpanel:categories_list")

    return render(
        request, "adminpanel/category_form.html", {"form": form, "category": None, "active_nav": "categories"}
    )


@api_staff_required
def category_edit(request, category_id):
    category = products_service.get_category(str(category_id))
    if category is None:
        raise Http404("Categoría no encontrada")

    token = auth_service.get_access_token(request)
    categories = products_service.list_all_categories()

    if request.method == "POST":
        form = CategoryForm(request.POST, categories=categories, exclude_id=str(category_id))
        if form.is_valid():
            try:
                products_service.update_category(token, str(category_id), form.to_api_payload())
            except ApiConflictError:
                form.add_error("name", "Ya existe una categoría con ese nombre.")
            except ApiValidationError:
                form.add_error(None, "Revisa los datos de la categoría.")
            except ApiError:
                form.add_error(None, "No fue posible actualizar la categoría.")
            else:
                messages.success(request, "Categoría actualizada.")
                return redirect("adminpanel:categories_list")
    else:
        form = CategoryForm(
            initial={
                "name": category["name"],
                "description": category.get("description"),
                "parent_id": category.get("parent_id") or "",
                "is_active": category["is_active"],
            },
            categories=categories,
            exclude_id=str(category_id),
        )

    return render(
        request, "adminpanel/category_form.html", {"form": form, "category": category, "active_nav": "categories"}
    )


@api_staff_required
@require_POST
def category_delete(request, category_id):
    token = auth_service.get_access_token(request)
    try:
        products_service.delete_category(token, str(category_id))
    except ApiConflictError:
        messages.error(request, "No se puede eliminar: la categoría tiene productos asociados.")
    except ApiError:
        messages.error(request, "No fue posible eliminar la categoría.")
    else:
        messages.success(request, "Categoría eliminada.")
    return redirect("adminpanel:categories_list")


# --- Inventory --------------------------------------------------------


INVENTORY_PAGE_SIZE = 50


def _page_number(value) -> int:
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return 1


def _redirect_to_inventory_page(request):
    """Back to the inventory page and filters the form was posted from
    (hidden `return_query` field), not always the unfiltered page 1.
    """
    query = QueryDict(request.POST.get("return_query", "")).urlencode()
    url = reverse("adminpanel:inventory_list")
    return redirect(f"{url}?{query}" if query else url)


@api_staff_required
def inventory_list(request):
    """One page of products (GET /products, by name, inactive ones included)
    joined to their stock rows from one GET /inventory filtered by those ids.
    Products with no inventory row still get a row ("Sin registro de
    inventario"). `stock=bajo` lists active products at or under their reorder
    level straight from GET /inventory instead; that endpoint has no category
    filter, so the category is dropped there.
    """
    token = auth_service.get_access_token(request)
    page = _page_number(request.GET.get("page"))
    categories = products_service.list_all_categories()
    search, category_id = product_filters(request, categories)
    low_stock_only = request.GET.get("stock") == "bajo"
    only_published = request.GET.get("estado") == "publicados"
    if low_stock_only:
        category_id = ""
        result = inventory_service.list_inventory(
            token, low_stock=True, search=search or None, page=page, page_size=INVENTORY_PAGE_SIZE
        )
        pairs = [
            (
                {"id": r["product_id"], "name": r["product_name"], "sku": r["product_sku"], "is_active": r["product_is_active"]},
                r,
            )
            for r in result["items"]
        ]
    else:
        result = products_service.list_products(
            category_id=category_id or None,
            search=search or None,
            page=page,
            page_size=INVENTORY_PAGE_SIZE,
            include_inactive=not only_published,
            token=token,
        )
        availability_by_id = inventory_service.availability_by_product(token, [p["id"] for p in result["items"]])
        pairs = [(product, availability_by_id.get(product["id"])) for product in result["items"]]

    rows = []
    for product, availability in pairs:
        rows.append(
            {
                "product": product,
                "availability": availability,
                "adjust_form": InventoryAdjustForm(prefix=product["id"]),
                "reorder_form": ReorderLevelForm(
                    prefix=product["id"],
                    initial={"reorder_level": availability["reorder_level"]} if availability else None,
                ),
            }
        )
    context = {
        "rows": rows,
        "categories": categories,
        "search": search,
        "category_id": category_id,
        "low_stock_only": low_stock_only,
        "only_published": only_published,
        "total": result["total"],
        "page": result["page"],
        "pages": result["pages"],
        "active_nav": "inventory",
    }
    return render(request, "adminpanel/inventory_list.html", context)


@api_staff_required
@require_POST
def inventory_adjust(request, product_id):
    token = auth_service.get_access_token(request)
    form = InventoryAdjustForm(request.POST, prefix=str(product_id))
    if form.is_valid():
        try:
            inventory_service.adjust_stock(
                token, str(product_id), form.cleaned_data["delta"], form.cleaned_data["reason"] or None
            )
        except ApiError:
            messages.error(request, "No fue posible ajustar el inventario.")
        else:
            messages.success(request, "Inventario ajustado.")
    else:
        messages.error(request, "Cantidad inválida.")
    return _redirect_to_inventory_page(request)


@api_staff_required
@require_POST
def inventory_set_reorder(request, product_id):
    token = auth_service.get_access_token(request)
    form = ReorderLevelForm(request.POST, prefix=str(product_id))
    if form.is_valid():
        availability = inventory_service.get_availability(str(product_id))
        current_on_hand = availability["quantity_on_hand"] if availability else 0
        try:
            inventory_service.set_levels(
                token, str(product_id), current_on_hand, form.cleaned_data["reorder_level"]
            )
        except ApiConflictError:
            messages.error(request, "El stock en bodega no puede quedar por debajo de lo reservado.")
        except ApiError:
            messages.error(request, "No fue posible actualizar el nivel de reorden.")
        else:
            messages.success(request, "Nivel de reorden actualizado.")
    else:
        messages.error(request, "Nivel inválido.")
    return _redirect_to_inventory_page(request)


@api_staff_required
def inventory_history(request, product_id):
    """Manual stock changes of one product (adjust / set levels), newest
    first: who, before/after, reason, when.
    """
    token = auth_service.get_access_token(request)
    product = products_service.get_product(str(product_id))
    if product is None:
        raise Http404("Producto no encontrado")

    page = _page_number(request.GET.get("page"))
    try:
        result = inventory_service.list_history(token, str(product_id), page=page, page_size=20)
    except ApiNotFoundError:
        raise Http404("Producto no encontrado") from None

    context = {
        "product": product,
        "availability": inventory_service.get_availability(str(product_id)),
        "entries": result["items"],
        "page": result["page"],
        "pages": result["pages"],
        "active_nav": "inventory",
    }
    return render(request, "adminpanel/inventory_history.html", context)


# --- Customers --------------------------------------------------------


@api_staff_required
def customers_list(request):
    token = auth_service.get_access_token(request)
    try:
        page = max(1, int(request.GET.get("page", 1)))
    except ValueError:
        page = 1

    search = request.GET.get("q", "").strip()[:100]
    result = customers_service.list_customers(token, page=page, page_size=20, search=search or None)
    context = {
        "customers": result["items"],
        "search": search,
        "total": result["total"],
        "page": result["page"],
        "pages": result["pages"],
        "active_nav": "customers",
    }
    return render(request, "adminpanel/customers_list.html", context)


@api_staff_required
def customer_detail(request, customer_id):
    token = auth_service.get_access_token(request)
    customer = customers_service.get_customer(token, str(customer_id))
    if customer is None:
        raise Http404("Cliente no encontrado")
    return render(
        request, "adminpanel/customer_detail.html", {"customer": customer, "active_nav": "customers"}
    )
