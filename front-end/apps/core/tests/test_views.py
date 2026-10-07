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


@pytest.mark.django_db
def test_pages_use_styled_confirm_dialog_not_native_confirm(client):
    """Destructive forms opt into the shared <dialog> (data-confirm) instead
    of the browser's native confirm()."""
    from pathlib import Path

    templates = Path(__file__).resolve().parents[3] / "templates"
    offenders = [
        str(p.relative_to(templates))
        for p in templates.rglob("*.html")
        if "confirm(" in p.read_text(encoding="utf-8")
    ]
    assert offenders == []

    html = client.get(reverse("core:home")).content.decode()
    assert 'id="confirm-dialog"' in html
