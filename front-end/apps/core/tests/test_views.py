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


@pytest.mark.django_db
def test_template_comments_do_not_leak_into_pages(client):
    """Django's {# #} only works on one line; a multi-line one is printed as
    text. Long comments must use {% comment %} ... {% endcomment %}."""
    from pathlib import Path

    templates = Path(__file__).resolve().parents[3] / "templates"
    offenders = [
        f"{p.relative_to(templates)}:{n}"
        for p in templates.rglob("*.html")
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
        if "{#" in line and "#}" not in line.split("{#", 1)[1]
    ]
    assert offenders == []

    html = client.get(reverse("core:home")).content.decode()
    assert "{#" not in html
    assert "#}" not in html


@pytest.mark.django_db
def test_home_shows_example_order_and_categories_with_products(client):
    content = client.get(reverse("core:home")).content.decode()
    assert "Así va un pedido" in content and "Ejemplo" in content
    assert "en la tienda." in content
    assert "Por categoría" in content
    assert "Ver las" in content and "categorías" in content
    assert "Lo más vendido" not in content and "Lo que más se lleva" not in content
