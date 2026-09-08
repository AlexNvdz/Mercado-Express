"""Tests for services/products.py in mock mode (forced by conftest.py)."""

from services import mock_data, products

ABARROTES_ID = mock_data.MOCK_CATEGORIES[0]["id"]
ARROZ_ID = mock_data.MOCK_PRODUCTS[0]["id"]


def test_list_categories_returns_envelope():
    result = products.list_categories()
    assert "items" in result and "total" in result
    assert len(result["items"]) > 0
    assert {"id", "name"} <= result["items"][0].keys()


def test_get_category_found():
    category = products.get_category(ABARROTES_ID)
    assert category is not None
    assert category["name"] == "Abarrotes"


def test_get_category_not_found():
    assert products.get_category("00000000-0000-0000-0000-000000000999") is None


def test_list_products_filters_by_category_id():
    all_products = products.list_products()["items"]
    abarrotes = products.list_products(category_id=ABARROTES_ID)["items"]
    assert 0 < len(abarrotes) < len(all_products)
    assert all(p["category_id"] == ABARROTES_ID for p in abarrotes)


def test_list_products_filters_by_search():
    results = products.list_products(search="arroz")["items"]
    assert len(results) == 1
    assert "arroz" in results[0]["name"].lower()


def test_get_product_found():
    product = products.get_product(ARROZ_ID)
    assert product is not None
    assert product["id"] == ARROZ_ID


def test_get_product_not_found():
    assert products.get_product("00000000-0000-0000-0000-000000000999") is None
