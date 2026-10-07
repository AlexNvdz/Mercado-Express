import pytest
from django.conf import settings
from django.urls import reverse

from services import mock_data
from services import orders as orders_service
from services.exceptions import ApiConflictError

ORDER_ID = mock_data.MOCK_ORDERS[0]["id"]
CATEGORY_ID = mock_data.MOCK_CATEGORIES[0]["id"]
PRODUCT_ID = mock_data.MOCK_PRODUCTS[0]["id"]
CUSTOMER_ID = mock_data.MOCK_CUSTOMERS[1]["id"]


def _login_as_customer(client):
    client.post(
        reverse("accounts:login"),
        {"email": "cliente.demo@mercadoexpress.test", "password": "demo1234"},
    )


def _login_as_staff(client):
    session = client.session
    session[settings.API_ACCESS_TOKEN_SESSION_KEY] = "mock-access-token"
    session[settings.API_ROLE_SESSION_KEY] = "admin"
    session.save()


def _order_in_status(status):
    """A fresh mock order (no shipment) forced into `status`, so tests don't
    mutate the seed orders other tests read.
    """
    order = orders_service.create_order(
        "any", [{"product_id": PRODUCT_ID, "quantity": 1}], shipping_address_id=mock_data.MOCK_ADDRESSES[0]["id"]
    )
    order["status"] = status
    return order


@pytest.mark.django_db
def test_home_requires_login(client):
    response = client.get(reverse("adminpanel:home"))
    assert response.status_code == 302
    assert reverse("accounts:login") in response.url


@pytest.mark.django_db
def test_home_blocks_non_staff(client):
    _login_as_customer(client)
    response = client.get(reverse("adminpanel:home"))
    assert response.status_code == 302
    assert response.url == reverse("core:home")


@pytest.mark.django_db
def test_home_loads_stats_for_staff(client):
    _login_as_staff(client)
    response = client.get(reverse("adminpanel:home"))
    assert response.status_code == 200
    assert b"Resumen" in response.content


@pytest.mark.django_db
def test_home_shows_net_gross_and_refunded_revenue(client, monkeypatch):
    summary = {
        **mock_data.MOCK_REPORT_SUMMARY,
        "net_revenue": "25000.00",
        "gross_revenue": "30600.00",
        "refunded_amount": "5600.00",
        "sale_count": 3,
        "reversal_count": 1,
    }
    monkeypatch.setattr("services.reports.get_summary", lambda token, **kwargs: summary)
    _login_as_staff(client)

    content = client.get(reverse("adminpanel:home")).content.decode()

    assert "Ingresos netos" in content
    assert "$25.000" in content
    assert "Brutos $30.600" in content
    assert "Reembolsos $5.600" in content
    assert "3 ventas · 1 reembolsada" in content


@pytest.mark.django_db
def test_home_resolves_low_stock_product_names(client):
    _login_as_staff(client)
    content = client.get(reverse("adminpanel:home")).content.decode()
    # MOCK_INVENTORY: only the detergent (0 on hand, reorder level 10) is low.
    assert "Detergente en polvo 1kg" in content


@pytest.mark.django_db
def test_core_home_redirects_staff_to_panel(client):
    _login_as_staff(client)
    response = client.get(reverse("core:home"))
    assert response.status_code == 302
    assert response.url == reverse("adminpanel:home")


@pytest.mark.django_db
def test_staff_can_create_and_delete_category(client):
    _login_as_staff(client)
    before = len(mock_data.MOCK_CATEGORIES)

    response = client.post(
        reverse("adminpanel:category_create"),
        {"name": "Bebidas", "description": "", "parent_id": "", "is_active": "on"},
    )
    assert response.status_code == 302
    assert len(mock_data.MOCK_CATEGORIES) == before + 1
    new_category = mock_data.MOCK_CATEGORIES[-1]

    response = client.post(reverse("adminpanel:category_delete", kwargs={"category_id": new_category["id"]}))
    assert response.status_code == 302
    assert len(mock_data.MOCK_CATEGORIES) == before


@pytest.mark.django_db
def test_duplicate_category_name_shows_spanish_error(client, monkeypatch):
    def raise_conflict(*args, **kwargs):
        raise ApiConflictError("409", status_code=409, payload={"detail": "Category 'Bebidas' already exists."})

    monkeypatch.setattr("apps.adminpanel.views.products_service.create_category", raise_conflict)
    _login_as_staff(client)

    response = client.post(
        reverse("adminpanel:category_create"),
        {"name": "Bebidas", "description": "", "parent_id": "", "is_active": "on"},
    )

    content = response.content.decode()
    assert response.status_code == 200
    assert "Ya existe una categoría con ese nombre." in content
    assert "already exists" not in content


@pytest.mark.django_db
def test_delete_category_with_products_shows_spanish_error(client, monkeypatch):
    english_detail = f"Category {CATEGORY_ID} still has 3 product(s); move or delete them first."

    def raise_conflict(*args, **kwargs):
        raise ApiConflictError("409", status_code=409, payload={"detail": english_detail})

    monkeypatch.setattr("apps.adminpanel.views.products_service.delete_category", raise_conflict)
    _login_as_staff(client)

    response = client.post(
        reverse("adminpanel:category_delete", kwargs={"category_id": CATEGORY_ID}), follow=True
    )

    content = response.content.decode()
    assert "la categoría tiene productos asociados" in content
    assert "still has" not in content


@pytest.mark.django_db
def test_staff_can_adjust_inventory(client):
    _login_as_staff(client)
    before = mock_data.MOCK_INVENTORY[PRODUCT_ID]["quantity_on_hand"]

    response = client.post(
        reverse("adminpanel:inventory_adjust", kwargs={"product_id": PRODUCT_ID}),
        {f"{PRODUCT_ID}-delta": 15, f"{PRODUCT_ID}-reason": "Restock"},
    )
    assert response.status_code == 302
    assert mock_data.MOCK_INVENTORY[PRODUCT_ID]["quantity_on_hand"] == before + 15


@pytest.mark.django_db
def test_inventory_list_shows_products_with_and_without_stock_row(client):
    no_row_id = mock_data.MOCK_PRODUCTS[1]["id"]
    del mock_data.MOCK_INVENTORY[no_row_id]
    _login_as_staff(client)

    response = client.get(reverse("adminpanel:inventory_list"))

    content = response.content.decode()
    assert response.status_code == 200
    for product in mock_data.MOCK_PRODUCTS:
        assert product["name"] in content
    assert content.count("Sin registro de inventario.") == 1


@pytest.mark.django_db
def test_inventory_list_batches_stock_reads_and_paginates(client, api_calls):
    """Real-API path: one GET /products page joined to the batched
    GET /inventory, never GET /inventory/{id} per product.
    """
    with_row = {"id": "00000000-0000-0000-0000-000000000901", "name": "Café molido", "sku": "SKU-CAF"}
    without_row = {"id": "00000000-0000-0000-0000-000000000902", "name": "Panela", "sku": "SKU-PAN"}

    def respond(method, path, kwargs):
        if path == "/api/v1/products":
            return {"items": [with_row, without_row], "total": 102, "page": 2, "page_size": 50, "pages": 3}
        if path == "/api/v1/inventory":
            row = {"product_id": with_row["id"], "quantity_on_hand": 7, "quantity_reserved": 2, "quantity_available": 5, "reorder_level": 3}
            return {"items": [row], "total": 1, "page": 1, "page_size": 100, "pages": 1}
        return {"items": [], "total": 0, "page": 1, "page_size": 8, "pages": 0}

    api_calls.response = respond
    _login_as_staff(client)

    response = client.get(reverse("adminpanel:inventory_list") + "?page=2")

    content = response.content.decode()
    assert response.status_code == 200
    assert "Café molido" in content and "Panela" in content
    assert "Sin registro de inventario." in content
    assert "Página 2 de 3" in content
    assert 'name="page" value="2"' in content
    paths = [path for _, path, _ in api_calls]
    assert not [path for path in paths if path.startswith("/api/v1/inventory/")]
    products_call = next(kwargs for _, path, kwargs in api_calls if path == "/api/v1/products")
    assert products_call["params"] == {"page": 2, "page_size": 50}


@pytest.mark.django_db
def test_inventory_adjust_returns_to_same_page(client):
    _login_as_staff(client)
    response = client.post(
        reverse("adminpanel:inventory_adjust", kwargs={"product_id": PRODUCT_ID}),
        {f"{PRODUCT_ID}-delta": 1, f"{PRODUCT_ID}-reason": "", "page": "2"},
    )
    assert response.url == reverse("adminpanel:inventory_list") + "?page=2"


@pytest.mark.django_db
def test_staff_can_set_reorder_level(client):
    _login_as_staff(client)
    response = client.post(
        reverse("adminpanel:inventory_set_reorder", kwargs={"product_id": PRODUCT_ID}),
        {f"{PRODUCT_ID}-reorder_level": 42},
    )
    assert response.url == reverse("adminpanel:inventory_list")
    assert mock_data.MOCK_INVENTORY[PRODUCT_ID]["reorder_level"] == 42


@pytest.mark.django_db
def test_staff_can_update_order_status(client):
    _login_as_staff(client)
    order = _order_in_status("paid")
    response = client.post(
        reverse("adminpanel:order_status_update", kwargs={"order_id": order["id"]}),
        {"status": "preparing"},
    )
    assert response.status_code == 302
    assert order["status"] == "preparing"


@pytest.mark.django_db
def test_manual_override_cannot_deliver_shipped_order(client):
    """shipped -> delivered only happens through the shipment's deliver step
    now, so a shipped order has no manual targets.
    """
    _login_as_staff(client)
    order_id = mock_data.MOCK_ORDERS[1]["id"]  # seeded "shipped"

    detail = client.get(reverse("adminpanel:order_detail", kwargs={"order_id": order_id})).content.decode()
    assert "Actualizar estado" not in detail
    assert "Márcalo como entregado desde el envío" in detail

    client.post(reverse("adminpanel:order_status_update", kwargs={"order_id": order_id}), {"status": "delivered"})
    order = next(o for o in mock_data.MOCK_ORDERS if o["id"] == order_id)
    assert order["status"] == "shipped"


@pytest.mark.django_db
def test_staff_cannot_force_invalid_order_status_transition(client):
    """ORDER_ID is "delivered" (terminal) -- the form has no valid choices
    for it, so posting any status is rejected without touching the order.
    """
    _login_as_staff(client)
    response = client.post(
        reverse("adminpanel:order_status_update", kwargs={"order_id": ORDER_ID}),
        {"status": "preparing"},
    )
    assert response.status_code == 302
    order = next(o for o in mock_data.MOCK_ORDERS if o["id"] == ORDER_ID)
    assert order["status"] == "delivered"


@pytest.mark.django_db
def test_order_detail_offers_shipment_form_for_preparing_order(client):
    """The bug: an order moved to "preparing" by hand could never get a
    shipment (and so a tracking number) because creation required "paid".
    """
    _login_as_staff(client)
    order = _order_in_status("preparing")
    content = client.get(reverse("adminpanel:order_detail", kwargs={"order_id": order["id"]})).content.decode()
    assert "Crear envío" in content
    assert "Número de guía" in content


@pytest.mark.django_db
def test_order_detail_hides_shipment_form_for_pending_order(client):
    _login_as_staff(client)
    order = _order_in_status("pending")
    content = client.get(reverse("adminpanel:order_detail", kwargs={"order_id": order["id"]})).content.decode()
    assert "Crear envío" not in content


@pytest.mark.django_db
@pytest.mark.parametrize("status", ["paid", "preparing"])
def test_staff_can_create_shipment_with_tracking_number(client, status):
    _login_as_staff(client)
    order = _order_in_status(status)

    response = client.post(
        reverse("adminpanel:shipment_create", kwargs={"order_id": order["id"]}),
        {"carrier": "Servientrega", "tracking_number": "SV-123"},
    )

    assert response.status_code == 302
    shipment = mock_data.MOCK_SHIPMENTS[order["id"]]
    assert shipment["carrier"] == "Servientrega"
    assert shipment["tracking_number"] == "SV-123"
    assert shipment["status"] == "preparing"
    assert order["status"] == "preparing"


@pytest.mark.django_db
def test_blank_carrier_and_tracking_number_are_sent_as_null(client):
    _login_as_staff(client)
    order = _order_in_status("paid")
    client.post(
        reverse("adminpanel:shipment_create", kwargs={"order_id": order["id"]}),
        {"carrier": "  ", "tracking_number": ""},
    )
    shipment = mock_data.MOCK_SHIPMENTS[order["id"]]
    assert shipment["carrier"] is None
    assert shipment["tracking_number"] is None


@pytest.mark.django_db
def test_create_shipment_conflict_shows_spanish_error(client, monkeypatch):
    def raise_conflict(*args, **kwargs):
        raise ApiConflictError("409", status_code=409, payload={"detail": "Order already has a shipment."})

    monkeypatch.setattr("apps.adminpanel.views.shipments_service.create_shipment", raise_conflict)
    _login_as_staff(client)
    order = _order_in_status("paid")

    response = client.post(
        reverse("adminpanel:shipment_create", kwargs={"order_id": order["id"]}),
        {"carrier": "", "tracking_number": "SV-1"},
        follow=True,
    )

    content = response.content.decode()
    assert "No se pudo crear el envío" in content
    assert "already has" not in content


@pytest.mark.django_db
def test_staff_can_edit_tracking_number_before_dispatch(client):
    _login_as_staff(client)
    order = _order_in_status("preparing")
    client.post(
        reverse("adminpanel:shipment_create", kwargs={"order_id": order["id"]}),
        {"carrier": "", "tracking_number": ""},
    )

    detail = client.get(reverse("adminpanel:order_detail", kwargs={"order_id": order["id"]})).content.decode()
    assert "Guardar datos del envío" in detail

    response = client.post(
        reverse("adminpanel:shipment_update", kwargs={"order_id": order["id"]}),
        {"carrier": "Coordinadora", "tracking_number": "CO-999"},
    )

    assert response.status_code == 302
    shipment = mock_data.MOCK_SHIPMENTS[order["id"]]
    assert shipment["carrier"] == "Coordinadora"
    assert shipment["tracking_number"] == "CO-999"


@pytest.mark.django_db
def test_editing_dispatched_shipment_shows_spanish_error(client):
    _login_as_staff(client)
    order_id = mock_data.MOCK_ORDERS[1]["id"]  # seeded shipment is in_transit

    detail = client.get(reverse("adminpanel:order_detail", kwargs={"order_id": order_id})).content.decode()
    assert "Guardar datos del envío" not in detail

    response = client.post(
        reverse("adminpanel:shipment_update", kwargs={"order_id": order_id}),
        {"carrier": "Otra", "tracking_number": "X-1"},
        follow=True,
    )

    assert "El envío ya fue despachado" in response.content.decode()
    assert mock_data.MOCK_SHIPMENTS[order_id]["tracking_number"] == "MANUAL-0000000002"


@pytest.mark.django_db
def test_ship_and_deliver_keep_tracking_number_and_close_order(client):
    _login_as_staff(client)
    order = _order_in_status("paid")
    client.post(
        reverse("adminpanel:shipment_create", kwargs={"order_id": order["id"]}),
        {"carrier": "Servientrega", "tracking_number": "SV-123"},
    )

    client.post(reverse("adminpanel:shipment_ship", kwargs={"order_id": order["id"]}))
    shipment = mock_data.MOCK_SHIPMENTS[order["id"]]
    assert shipment["status"] == "in_transit"
    assert shipment["tracking_number"] == "SV-123"
    assert order["status"] == "shipped"

    client.post(reverse("adminpanel:shipment_deliver", kwargs={"order_id": order["id"]}))
    assert shipment["status"] == "delivered"
    assert order["status"] == "delivered"


@pytest.mark.django_db
def test_manual_cancel_cancels_undispatched_shipment(client):
    _login_as_staff(client)
    order = _order_in_status("paid")
    client.post(
        reverse("adminpanel:shipment_create", kwargs={"order_id": order["id"]}),
        {"carrier": "", "tracking_number": ""},
    )

    client.post(
        reverse("adminpanel:order_status_update", kwargs={"order_id": order["id"]}), {"status": "cancelled"}
    )

    assert order["status"] == "cancelled"
    assert mock_data.MOCK_SHIPMENTS[order["id"]]["status"] == "cancelled"
    detail = client.get(reverse("adminpanel:order_detail", kwargs={"order_id": order["id"]})).content.decode()
    assert "status--cancelled" in detail
    assert "Marcar despachado" not in detail
    assert "Guardar datos del envío" not in detail


@pytest.mark.django_db
def test_customers_list_requires_staff(client):
    _login_as_customer(client)
    response = client.get(reverse("adminpanel:customers_list"))
    assert response.status_code == 302
    assert response.url == reverse("core:home")


@pytest.mark.django_db
def test_customers_list_loads_for_staff(client):
    _login_as_staff(client)
    response = client.get(reverse("adminpanel:customers_list"))
    assert response.status_code == 200
    assert b"Ana Torres" in response.content


@pytest.mark.django_db
def test_customer_detail_loads_for_staff(client):
    _login_as_staff(client)
    response = client.get(reverse("adminpanel:customer_detail", kwargs={"customer_id": CUSTOMER_ID}))
    assert response.status_code == 200
    assert b"Ana Torres" in response.content
