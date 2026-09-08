import pytest
from django.urls import reverse


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
        {
            "line1": "Calle 1 # 2-3",
            "city": "Cali",
            "state": "Valle del Cauca",
            "postal_code": "760001",
            "country": "CO",
        },
    )
    assert response.status_code == 302
    assert response.url == reverse("dashboard:addresses")
