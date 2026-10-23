import pytest
from django.conf import settings
from django.urls import reverse

from services import mock_data

ARROZ_ID = mock_data.MOCK_PRODUCTS[0]["id"]
CATEGORY_ID = mock_data.MOCK_CATEGORIES[0]["id"]


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


@pytest.mark.django_db
def test_admin_list_requires_login(client):
    response = client.get(reverse("catalog:admin_list"))
    assert response.status_code == 302
    assert reverse("accounts:login") in response.url


@pytest.mark.django_db
def test_admin_list_blocks_non_staff(client):
    _login_as_customer(client)
    response = client.get(reverse("catalog:admin_list"))
    assert response.status_code == 302
    assert response.url == reverse("core:home")


@pytest.mark.django_db
def test_admin_list_loads_for_staff(client):
    _login_as_staff(client)
    response = client.get(reverse("catalog:admin_list"))
    assert response.status_code == 200
    assert b"Arroz blanco" in response.content


@pytest.mark.django_db
def test_admin_list_keeps_hidden_products_visible_to_staff(client):
    mock_data.MOCK_PRODUCTS[0]["is_active"] = False
    _login_as_staff(client)
    content = client.get(reverse("catalog:admin_list")).content.decode()
    assert "Arroz blanco" in content
    assert "Oculto" in content


@pytest.mark.django_db
def test_admin_list_asks_backend_for_inactive_products(client, api_calls):
    api_calls.response = {"items": [], "total": 0, "page": 1, "page_size": 100, "pages": 0}
    _login_as_staff(client)
    client.get(reverse("catalog:admin_list"))
    products_call = next(kwargs for _, path, kwargs in api_calls if path == "/api/v1/products")
    assert products_call["params"]["include_inactive"] == "true"
    assert products_call["token"] == "mock-access-token"


def _paged_products_api(api_calls, category_id):
    def respond(method, path, kwargs):
        if path == "/api/v1/categories":
            return {"items": [{"id": category_id, "name": "Granos"}], "total": 1, "page": 1, "page_size": 100, "pages": 1}
        product = {"id": "00000000-0000-0000-0000-000000000991", "name": "Café molido", "sku": "CAF-1", "price": "9000.00", "is_active": True, "images": []}
        return {"items": [product], "total": 120, "page": 2, "page_size": 50, "pages": 3}

    api_calls.response = respond


@pytest.mark.django_db
def test_admin_list_sends_search_category_and_page(client, api_calls):
    category_id = "00000000-0000-0000-0000-000000000101"
    _paged_products_api(api_calls, category_id)
    _login_as_staff(client)

    content = client.get(reverse("catalog:admin_list"), {"q": "café", "category": category_id, "page": 2}).content.decode()

    products_call = next(kwargs for _, path, kwargs in api_calls if path == "/api/v1/products")
    assert products_call["params"] == {
        "page": 2, "page_size": 50, "category_id": category_id, "search": "café", "include_inactive": "true"
    }
    assert "120 productos con estos filtros" in content
    assert "Página 2 de 3" in content
    assert "page=3" in content and "q=caf%C3%A9" in content  # pagination links keep the filters


@pytest.mark.django_db
def test_admin_list_published_only_and_unknown_category(client, api_calls):
    _paged_products_api(api_calls, "00000000-0000-0000-0000-000000000101")
    _login_as_staff(client)

    client.get(reverse("catalog:admin_list"), {"estado": "publicados", "category": "not-a-uuid"})

    products_call = next(kwargs for _, path, kwargs in api_calls if path == "/api/v1/products")
    assert "include_inactive" not in products_call["params"]
    assert "category_id" not in products_call["params"]


@pytest.mark.django_db
def test_staff_can_create_product(client):
    _login_as_staff(client)
    response = client.post(
        reverse("catalog:admin_create"),
        {
            "sku": "NEW-SKU-001",
            "name": "Producto nuevo",
            "description": "",
            "category_id": CATEGORY_ID,
            "price": "12.50",
            "is_active": "on",
        },
    )
    assert response.status_code == 302
    assert any(p["sku"] == "NEW-SKU-001" for p in mock_data.MOCK_PRODUCTS)


@pytest.mark.django_db
def test_staff_can_edit_product(client):
    _login_as_staff(client)
    response = client.post(
        reverse("catalog:admin_edit", kwargs={"product_id": ARROZ_ID}),
        {
            "sku": mock_data.MOCK_PRODUCTS[0]["sku"],
            "name": "Arroz blanco 1kg (editado)",
            "description": "",
            "category_id": CATEGORY_ID,
            "price": "6500.00",
            "is_active": "on",
        },
    )
    assert response.status_code == 302

    updated = client.get(reverse("catalog:admin_edit", kwargs={"product_id": ARROZ_ID}))
    assert b"Arroz blanco 1kg (editado)" in updated.content


@pytest.mark.django_db
def test_staff_can_delete_product(client):
    _login_as_staff(client)
    before = len(mock_data.MOCK_PRODUCTS)
    response = client.post(reverse("catalog:admin_delete", kwargs={"product_id": ARROZ_ID}))
    assert response.status_code == 302
    assert len(mock_data.MOCK_PRODUCTS) == before - 1


@pytest.mark.django_db
def test_image_upload_requires_staff(client):
    _login_as_customer(client)
    response = client.post(reverse("catalog:admin_upload_image", kwargs={"product_id": ARROZ_ID}))
    assert response.status_code == 302
    assert response.url == reverse("core:home")
