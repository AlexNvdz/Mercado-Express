import pytest
from django.urls import reverse

from services import mock_data

ARROZ_ID = mock_data.MOCK_PRODUCTS[0]["id"]


def _login(client):
    client.post(
        reverse("accounts:login"),
        {"email": "cliente.demo@mercadoexpress.test", "password": "demo1234"},
    )


@pytest.mark.django_db
def test_order_list_requires_login(client):
    response = client.get(reverse("orders:list"))
    assert response.status_code == 302


@pytest.mark.django_db
def test_order_list_shows_orders_when_logged_in(client):
    _login(client)
    response = client.get(reverse("orders:list"))
    assert response.status_code == 200
    assert b"ORD-DEMO0001" in response.content


@pytest.mark.django_db
def test_order_detail_shows_shipment_tracking(client):
    _login(client)
    order_id = mock_data.MOCK_ORDERS[0]["id"]
    response = client.get(reverse("orders:detail", kwargs={"order_id": order_id}))
    assert response.status_code == 200
    assert b"MANUAL-0000000001" in response.content


@pytest.mark.django_db
def test_order_detail_404_for_unknown_order(client):
    _login(client)
    unknown_id = "00000000-0000-0000-0000-000000000999"
    response = client.get(reverse("orders:detail", kwargs={"order_id": unknown_id}))
    assert response.status_code == 404


@pytest.mark.django_db
def test_checkout_empty_cart_redirects_to_cart(client):
    _login(client)
    response = client.get(reverse("orders:checkout"))
    assert response.status_code == 302
    assert response.url == reverse("cart:detail")


@pytest.mark.django_db
def test_checkout_without_saved_address_redirects_to_add_address(client, monkeypatch):
    _login(client)
    client.post(reverse("cart:add", kwargs={"product_id": ARROZ_ID}), {"quantity": 1})
    monkeypatch.setattr("apps.orders.views.customers_service.list_addresses", lambda token: [])

    response = client.get(reverse("orders:checkout"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("dashboard:address_add"))


@pytest.mark.django_db
def test_checkout_shows_address_choices(client):
    _login(client)
    client.post(reverse("cart:add", kwargs={"product_id": ARROZ_ID}), {"quantity": 2})
    response = client.get(reverse("orders:checkout"))
    assert response.status_code == 200
    assert b"Bogot" in response.content


@pytest.mark.django_db
def test_checkout_creates_order_pays_and_clears_cart(client):
    _login(client)
    client.post(reverse("cart:add", kwargs={"product_id": ARROZ_ID}), {"quantity": 2})
    address_id = mock_data.MOCK_ADDRESSES[0]["id"]

    response = client.post(reverse("orders:checkout"), {"shipping_address_id": address_id})
    assert response.status_code == 302

    order_response = client.get(response.url)
    assert order_response.status_code == 200
    assert b"paid" in order_response.content  # payment auto-completes per API_CONTRACT.md

    cart_response = client.get(reverse("cart:detail"))
    assert "vacío" in cart_response.content.decode()


@pytest.mark.django_db
def test_checkout_out_of_stock_product_redirects_to_cart(client):
    _login(client)
    # Add a product to the cart, then corrupt its id in the session to
    # simulate the backend's 409 (product no longer available) response.
    client.post(reverse("cart:add", kwargs={"product_id": ARROZ_ID}), {"quantity": 1})
    session = client.session
    session["cart"] = {"00000000-0000-0000-0000-000000000999": 1}
    session.save()

    address_id = mock_data.MOCK_ADDRESSES[0]["id"]
    response = client.post(reverse("orders:checkout"), {"shipping_address_id": address_id})
    assert response.status_code == 302
    assert response.url == reverse("cart:detail")


@pytest.mark.django_db
def test_order_list_status_tabs_filter(client):
    _login(client)
    delivered_id = mock_data.MOCK_ORDERS[0]["id"]  # seeded "delivered"
    shipped_id = mock_data.MOCK_ORDERS[1]["id"]  # seeded "shipped"

    response = client.get(reverse("orders:list"), {"status": "delivered"})
    assert response.status_code == 200
    order_numbers = [o["order_number"] for o in response.context["orders"]]
    assert mock_data.MOCK_ORDERS[0]["order_number"] in order_numbers
    assert mock_data.MOCK_ORDERS[1]["order_number"] not in order_numbers


@pytest.mark.django_db
def test_reorder_adds_items_to_cart_and_redirects(client):
    _login(client)
    order_id = mock_data.MOCK_ORDERS[0]["id"]  # has 2 line items in mock data

    response = client.post(reverse("orders:reorder", kwargs={"order_id": order_id}))
    assert response.status_code == 302
    assert response.url == reverse("cart:detail")

    cart_response = client.get(reverse("cart:detail"))
    assert b"Arroz blanco 1kg" in cart_response.content


@pytest.mark.django_db
def test_reorder_requires_login(client):
    order_id = mock_data.MOCK_ORDERS[0]["id"]
    response = client.post(reverse("orders:reorder", kwargs={"order_id": order_id}))
    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))


@pytest.mark.django_db
def test_order_detail_shows_tracker_for_active_order(client):
    _login(client)
    order_id = mock_data.MOCK_ORDERS[1]["id"]  # seeded "shipped"
    response = client.get(reverse("orders:detail", kwargs={"order_id": order_id}))
    assert response.status_code == 200
    assert b"order-tracker" in response.content


@pytest.mark.django_db
def test_cancel_pending_order(client):
    _login(client)
    client.post(reverse("cart:add", kwargs={"product_id": ARROZ_ID}), {"quantity": 1})
    address_id = mock_data.MOCK_ADDRESSES[0]["id"]

    # Create an order via services directly so it stays "pending" (checkout
    # would auto-pay it, moving it out of the cancellable state).
    from services import orders as orders_service

    order = orders_service.create_order(
        "any", [{"product_id": ARROZ_ID, "quantity": 1}], shipping_address_id=address_id
    )

    response = client.post(reverse("orders:cancel", kwargs={"order_id": order["id"]}))
    assert response.status_code == 302

    detail = client.get(reverse("orders:detail", kwargs={"order_id": order["id"]}))
    assert b"cancelled" in detail.content
