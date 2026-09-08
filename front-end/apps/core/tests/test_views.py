import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_home_page_loads(client):
    response = client.get(reverse("core:home"))
    assert response.status_code == 200
    assert b"MercadoExpress" in response.content


@pytest.mark.django_db
def test_home_page_lists_categories(client):
    response = client.get(reverse("core:home"))
    assert b"Abarrotes" in response.content
