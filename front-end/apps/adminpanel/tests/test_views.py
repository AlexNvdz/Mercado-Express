import pytest
from django.conf import settings
from django.urls import reverse

from services import mock_data
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
def test_staff_can_update_order_status(client):
    _login_as_staff(client)
    # MOCK_ORDERS[1] starts "shipped" -- the only valid next status is
    # "delivered" (services/orders.py::ORDER_TRANSITIONS), which the
    # status-override form now restricts its choices to.
    order_id = mock_data.MOCK_ORDERS[1]["id"]
    response = client.post(
        reverse("adminpanel:order_status_update", kwargs={"order_id": order_id}),
        {"status": "delivered"},
    )
    assert response.status_code == 302
    order = next(o for o in mock_data.MOCK_ORDERS if o["id"] == order_id)
    assert order["status"] == "delivered"


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
