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
