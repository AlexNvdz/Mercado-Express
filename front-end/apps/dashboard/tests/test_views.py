import pytest
from django.urls import reverse

from services import mock_data
from services.exceptions import ApiValidationError

ADDRESS_ID = mock_data.MOCK_ADDRESSES[0]["id"]


def _login(client):
    client.post(
        reverse("accounts:login"),
        {"email": "cliente.demo@mercadoexpress.test", "password": "demo1234"},
    )


@pytest.mark.django_db
def test_profile_requires_login(client):
    response = client.get(reverse("dashboard:profile"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))


@pytest.mark.django_db
def test_profile_shows_user_data_when_logged_in(client):
    _login(client)
    response = client.get(reverse("dashboard:profile"))
    assert response.status_code == 200
    assert b"cliente.demo@mercadoexpress.test" in response.content


@pytest.mark.django_db
def test_address_list_requires_login(client):
    response = client.get(reverse("dashboard:addresses"))
    assert response.status_code == 302


@pytest.mark.django_db
def test_address_list_shows_saved_addresses(client):
    _login(client)
    response = client.get(reverse("dashboard:addresses"))
    assert response.status_code == 200
    assert b"Bogot" in response.content


@pytest.mark.django_db
def test_address_add_creates_and_redirects(client):
    _login(client)
    response = client.post(
        reverse("dashboard:address_add"),
        {"line1": "Calle 1 # 2-3", "city": "Cali", "state": "Valle del Cauca", "phone": "3001112233"},
    )
    assert response.status_code == 302
    assert response.url == reverse("dashboard:addresses")
    saved = mock_data.MOCK_ADDRESSES[-1]
    assert (saved["country"], saved["phone"]) == ("CO", "3001112233")


@pytest.mark.django_db
def test_address_add_shows_the_backend_reason_on_the_city(client, monkeypatch):
    def reject(*args, **kwargs):
        detail = "La ciudad 'Calli' no existe en el departamento 'Valle del Cauca'."
        raise ApiValidationError("422", status_code=422, payload={"detail": detail})

    monkeypatch.setattr("apps.dashboard.views.customers_service.add_address", reject)
    _login(client)
    response = client.post(
        reverse("dashboard:address_add"),
        {"line1": "Calle 1 # 2-3", "city": "Calli", "state": "Valle del Cauca", "phone": "3001112233"},
    )
    assert response.status_code == 200
    assert "no existe en el departamento" in response.content.decode()


@pytest.mark.django_db
def test_address_form_lists_departments_and_cities(client):
    _login(client)
    content = client.get(reverse("dashboard:address_add")).content.decode()
    assert '<option value="Antioquia">' in content
    assert 'list="city-options"' in content
    cities = client.get(reverse("dashboard:address_cities"), {"departamento": "Antioquia"})
    assert cities.json() == ["Envigado", "Medellín"]
    assert client.get(reverse("dashboard:address_cities")).json() == []


@pytest.mark.django_db
def test_address_set_default_redirects(client):
    _login(client)
    response = client.post(reverse("dashboard:address_set_default", kwargs={"address_id": ADDRESS_ID}))
    assert response.status_code == 302
    assert response.url == reverse("dashboard:addresses")


@pytest.mark.django_db
def test_profile_update_changes_full_name(client):
    _login(client)
    response = client.post(reverse("dashboard:profile"), {"full_name": "Nuevo Nombre", "phone": ""})
    assert response.status_code == 302

    profile_response = client.get(reverse("dashboard:profile"))
    assert b"Nuevo Nombre" in profile_response.content
