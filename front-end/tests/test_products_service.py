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


def test_list_products_hides_inactive_by_default():
    mock_data.MOCK_PRODUCTS[0]["is_active"] = False
    names = [p["name"] for p in products.list_products(page_size=100)["items"]]
    assert mock_data.MOCK_PRODUCTS[0]["name"] not in names


def test_list_products_include_inactive_returns_them():
    mock_data.MOCK_PRODUCTS[0]["is_active"] = False
    result = products.list_products(page_size=100, include_inactive=True, token="tok")
    assert result["total"] == len(mock_data.MOCK_PRODUCTS)


def test_include_inactive_is_sent_with_staff_token(api_calls):
    api_calls.response = {"items": [], "total": 0, "page": 1, "page_size": 50, "pages": 0}
    products.list_products(page=1, page_size=50, include_inactive=True, token="tok")
    method, path, kwargs = api_calls[0]
    assert (method, path) == ("GET", "/api/v1/products")
    assert kwargs["params"] == {"page": 1, "page_size": 50, "include_inactive": "true"}
    assert kwargs["token"] == "tok"


def test_public_listing_sends_neither_flag_nor_token(api_calls):
    api_calls.response = {"items": [], "total": 0, "page": 1, "page_size": 24, "pages": 0}
    products.list_products()
    _, _, kwargs = api_calls[0]
    assert "include_inactive" not in kwargs["params"]
    assert "token" not in kwargs
