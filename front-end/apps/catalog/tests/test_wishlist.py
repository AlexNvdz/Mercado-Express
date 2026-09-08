import pytest
from django.urls import reverse

from apps.catalog.wishlist import Wishlist
from services import mock_data

ARROZ_ID = mock_data.MOCK_PRODUCTS[0]["id"]
ACEITE_ID = mock_data.MOCK_PRODUCTS[1]["id"]


def test_toggle_adds_then_removes():
    wishlist = Wishlist({})
    assert wishlist.toggle(ARROZ_ID) is True
    assert wishlist.contains(ARROZ_ID) is True
    assert len(wishlist) == 1

    assert wishlist.toggle(ARROZ_ID) is False
    assert wishlist.contains(ARROZ_ID) is False
    assert len(wishlist) == 0


def test_iteration_yields_product_data():
    wishlist = Wishlist({})
    wishlist.toggle(ARROZ_ID)
    wishlist.toggle(ACEITE_ID)
    products = list(wishlist)
    assert {p["id"] for p in products} == {ARROZ_ID, ACEITE_ID}


@pytest.mark.django_db
def test_wishlist_toggle_view_redirects(client):
    response = client.post(reverse("catalog:wishlist_toggle", kwargs={"product_id": ARROZ_ID}))
    assert response.status_code == 302


@pytest.mark.django_db
def test_wishlist_page_shows_favorited_product(client):
    client.post(reverse("catalog:wishlist_toggle", kwargs={"product_id": ARROZ_ID}))
    response = client.get(reverse("catalog:wishlist"))
    assert response.status_code == 200
    assert b"Arroz blanco 1kg" in response.content


@pytest.mark.django_db
def test_wishlist_page_empty_state_by_default(client):
    response = client.get(reverse("catalog:wishlist"))
    assert response.status_code == 200
    assert "favoritos" in response.content.decode().lower()
