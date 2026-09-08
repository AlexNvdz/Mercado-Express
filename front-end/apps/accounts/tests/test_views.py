import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_login_page_loads(client):
    response = client.get(reverse("accounts:login"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_login_success_redirects_to_dashboard(client):
    response = client.post(
        reverse("accounts:login"),
        {"email": "cliente.demo@mercadoexpress.test", "password": "demo1234"},
    )
    assert response.status_code == 302
    assert response.url == reverse("dashboard:home")


@pytest.mark.django_db
def test_login_success_stores_token_pair_in_session(client):
    client.post(
        reverse("accounts:login"),
        {"email": "cliente.demo@mercadoexpress.test", "password": "demo1234"},
    )
    session = client.session
    assert session.get("mercadoexpress_access_token")
    assert session.get("mercadoexpress_refresh_token")


@pytest.mark.django_db
def test_login_failure_shows_error(client):
    response = client.post(
        reverse("accounts:login"),
        {"email": "cliente.demo@mercadoexpress.test", "password": "wrong"},
    )
    assert response.status_code == 200
    assert b"incorrectos" in response.content


@pytest.mark.django_db
def test_register_page_loads(client):
    response = client.get(reverse("accounts:register"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_register_success_redirects_to_login(client):
    response = client.post(
        reverse("accounts:register"),
        {
            "full_name": "Nueva Persona",
            "email": "nueva@example.com",
            "phone": "+57 300 111 2222",
            "password": "supersecreta1",
            "password_confirm": "supersecreta1",
        },
    )
    assert response.status_code == 302
    assert response.url == reverse("accounts:login")


@pytest.mark.django_db
def test_register_password_mismatch_shows_error(client):
    response = client.post(
        reverse("accounts:register"),
        {
            "full_name": "Nueva Persona",
            "email": "nueva@example.com",
            "password": "supersecreta1",
            "password_confirm": "otra-cosa",
        },
    )
    assert response.status_code == 200
    assert b"no coinciden" in response.content


@pytest.mark.django_db
def test_logout_clears_session(client):
    client.post(
        reverse("accounts:login"),
        {"email": "cliente.demo@mercadoexpress.test", "password": "demo1234"},
    )
    response = client.get(reverse("accounts:logout"))
    assert response.status_code == 302
    assert response.url == reverse("core:home")
    assert not client.session.get("mercadoexpress_access_token")
