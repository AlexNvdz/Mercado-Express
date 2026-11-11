"""Refund-claim widget: the JSON views behind templates/partials/support_chat.html."""

import pytest
from django.urls import reverse

from services import mock_data
from services import support as support_service
from services.exceptions import ApiTimeoutError

DELIVERED_ID = mock_data.MOCK_ORDERS[0]["id"]  # ORD-DEMO0001, delivered
SHIPPED_ID = mock_data.MOCK_ORDERS[1]["id"]  # ORD-DEMO0002, shipped


def _login(client):
    client.post(
        reverse("accounts:login"),
        {"email": "cliente.demo@mercadoexpress.test", "password": "demo1234"},
    )


@pytest.mark.django_db
def test_widget_only_for_logged_in_customers(client):
    assert b"data-claim" not in client.get(reverse("core:home")).content
    _login(client)
    assert b"data-claim" in client.get(reverse("core:home")).content


@pytest.mark.django_db
def test_claim_views_answer_401_json_without_login(client):
    assert client.get(reverse("orders:claim_orders")).status_code == 401
    response = client.post(reverse("orders:claim"), {"order_id": DELIVERED_ID, "mensaje": "quiero mi reembolso"})
    assert response.status_code == 401
    assert "error" in response.json()


@pytest.mark.django_db
def test_claim_orders_lists_only_delivered(client):
    _login(client)
    orders = client.get(reverse("orders:claim_orders")).json()["orders"]
    assert [o["order_number"] for o in orders] == ["ORD-DEMO0001"]
    assert orders[0]["created"] == "20/08/2026"


@pytest.mark.django_db
def test_claim_approved_refunds_delivered_order(client):
    _login(client)
    response = client.post(
        reverse("orders:claim"), {"order_id": DELIVERED_ID, "mensaje": "La leche llegó rota, devuélvanme la plata"}
    )
    assert response.status_code == 200
    assert response.json() == {
        "decision": "aprobado",
        "motivo": "Reembolso aprobado.",
        "order_status_label": "Reembolsado",
        "order_url": reverse("orders:detail", kwargs={"order_id": DELIVERED_ID}),
    }
    assert mock_data.MOCK_ORDERS[0]["status"] == "refunded"


@pytest.mark.django_db
def test_claim_without_refund_request_goes_to_manual_review(client):
    _login(client)
    data = client.post(reverse("orders:claim"), {"order_id": SHIPPED_ID, "mensaje": "¿dónde está mi pedido?"}).json()
    assert data["decision"] == "revision_manual"
    assert mock_data.MOCK_ORDERS[1]["status"] == "shipped"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "form",
    [
        {"order_id": "ORD-DEMO0001", "mensaje": "quiero mi reembolso"},
        {"order_id": DELIVERED_ID, "mensaje": "   corto   "},
        {"order_id": DELIVERED_ID, "mensaje": "x" * 1901},
    ],
)
def test_claim_rejects_bad_input_before_calling_backend(client, form):
    _login(client)
    response = client.post(reverse("orders:claim"), form)
    assert response.status_code == 400
    assert mock_data.MOCK_ORDERS[0]["status"] == "delivered"


@pytest.mark.django_db
def test_claim_timeout_answers_504(client, monkeypatch):
    _login(client)

    def slow(*args, **kwargs):
        raise ApiTimeoutError("Timed out")

    monkeypatch.setattr(support_service, "procesar_reclamo", slow)
    response = client.post(reverse("orders:claim"), {"order_id": DELIVERED_ID, "mensaje": "quiero mi reembolso"})
    assert response.status_code == 504
    assert response.json()["error"] == "El asistente tardó demasiado. Intenta de nuevo."


def test_service_writes_the_order_uuid_into_the_message(api_calls):
    api_calls.response = {"decision": "revision_manual", "motivo": "x", "order_id": None, "order_status": None}
    support_service.procesar_reclamo("tok", DELIVERED_ID, "llegó roto")
    [(method, path, kwargs)] = api_calls
    assert (method, path) == ("POST", "/api/v1/soporte/procesar-reclamo")
    assert kwargs["json"] == {"mensaje": f"Pedido {DELIVERED_ID}: llegó roto"}
    assert support_service._claims_client.timeout == support_service.CLAIM_TIMEOUT_SECONDS == 65


@pytest.mark.django_db
def test_order_detail_offers_claim_only_when_delivered(client):
    _login(client)
    delivered = client.get(reverse("orders:detail", kwargs={"order_id": DELIVERED_ID})).content
    shipped = client.get(reverse("orders:detail", kwargs={"order_id": SHIPPED_ID})).content
    assert b"data-claim-open" in delivered
    assert b"data-claim-open" not in shipped
