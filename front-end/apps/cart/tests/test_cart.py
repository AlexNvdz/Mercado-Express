import pytest
from django.urls import reverse

from apps.cart.cart import Cart
from services import mock_data

ARROZ_ID = mock_data.MOCK_PRODUCTS[0]["id"]
ACEITE_ID = mock_data.MOCK_PRODUCTS[1]["id"]


@pytest.fixture
def session_dict():
    return {}


def test_add_and_len(session_dict):
    cart = Cart(session_dict)
    cart.add(ARROZ_ID, 2)
    assert len(cart) == 2


def test_add_accumulates(session_dict):
    cart = Cart(session_dict)
    cart.add(ARROZ_ID, 2)
    cart.add(ARROZ_ID, 3)
    assert len(cart) == 5


def test_update_sets_quantity(session_dict):
    cart = Cart(session_dict)
    cart.add(ARROZ_ID, 2)
    cart.update(ARROZ_ID, 5)
    assert len(cart) == 5


def test_update_zero_removes_item(session_dict):
    cart = Cart(session_dict)
    cart.add(ARROZ_ID, 2)
    cart.update(ARROZ_ID, 0)
    assert len(cart) == 0


def test_remove(session_dict):
    cart = Cart(session_dict)
    cart.add(ARROZ_ID, 2)
    cart.remove(ARROZ_ID)
    assert len(cart) == 0


def test_clear(session_dict):
    cart = Cart(session_dict)
    cart.add(ARROZ_ID, 2)
    cart.add(ACEITE_ID, 1)
    cart.clear()
    assert len(cart) == 0


def test_iteration_enriches_with_product_data(session_dict):
    cart = Cart(session_dict)
    cart.add(ARROZ_ID, 2)
    items = list(cart)
    assert len(items) == 1
    assert items[0]["product"]["id"] == ARROZ_ID
    assert items[0]["quantity"] == 2
    assert items[0]["subtotal"] == items[0]["unit_price"] * 2


def test_as_order_items(session_dict):
    cart = Cart(session_dict)
    cart.add(ARROZ_ID, 2)
    cart.add(ACEITE_ID, 1)
    order_items = cart.as_order_items()
    assert {"product_id": ARROZ_ID, "quantity": 2} in order_items
    assert {"product_id": ACEITE_ID, "quantity": 1} in order_items


@pytest.mark.django_db
def test_add_to_cart_view_redirects(client):
    response = client.post(reverse("cart:add", kwargs={"product_id": ARROZ_ID}), {"quantity": 1})
    assert response.status_code == 302


@pytest.mark.django_db
def test_cart_detail_shows_added_item(client):
    client.post(reverse("cart:add", kwargs={"product_id": ARROZ_ID}), {"quantity": 2})
    response = client.get(reverse("cart:detail"))
    assert response.status_code == 200
    assert b"Arroz blanco 1kg" in response.content
