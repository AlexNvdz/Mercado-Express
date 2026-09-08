import pytest
from django.urls import reverse

from services import mock_data

ABARROTES_ID = mock_data.MOCK_CATEGORIES[0]["id"]
LACTEOS_ID = mock_data.MOCK_CATEGORIES[2]["id"]
ARROZ_ID = mock_data.MOCK_PRODUCTS[0]["id"]


@pytest.mark.django_db
def test_product_list_loads(client):
    response = client.get(reverse("catalog:list"))
    assert response.status_code == 200
    assert b"Arroz blanco" in response.content


@pytest.mark.django_db
def test_product_list_filters_by_category(client):
    url = reverse("catalog:category", kwargs={"category_id": LACTEOS_ID})
    response = client.get(url)
    assert response.status_code == 200
    assert b"Leche entera" in response.content
    assert b"Detergente" not in response.content


@pytest.mark.django_db
def test_product_detail_loads(client):
    url = reverse("catalog:detail", kwargs={"product_id": ARROZ_ID})
    response = client.get(url)
    assert response.status_code == 200
    assert b"Arroz blanco 1kg" in response.content


@pytest.mark.django_db
def test_product_detail_shows_availability(client):
    url = reverse("catalog:detail", kwargs={"product_id": ARROZ_ID})
    response = client.get(url)
    assert "En stock".encode() in response.content


@pytest.mark.django_db
def test_product_detail_404_for_unknown_id(client):
    url = reverse("catalog:detail", kwargs={"product_id": "00000000-0000-0000-0000-000000000999"})
    response = client.get(url)
    assert response.status_code == 404


@pytest.mark.django_db
def test_product_list_search_via_query_param(client):
    response = client.get(reverse("catalog:list"), {"q": "arroz"})
    assert response.status_code == 200
    assert b"Arroz blanco" in response.content
    assert b"Leche entera" not in response.content


@pytest.mark.django_db
def test_product_list_accepts_page_param_without_error(client):
    response = client.get(reverse("catalog:list"), {"page": 2})
    assert response.status_code == 200


@pytest.mark.django_db
def test_product_price_is_formatted_with_thousands_separator(client):
    url = reverse("catalog:detail", kwargs={"product_id": ARROZ_ID})
    response = client.get(url)
    assert b"6.500" in response.content
