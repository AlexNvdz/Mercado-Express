"""POST /soporte/procesar-reclamo. The LLM is replaced by a stub returning a
fixed intent, so these tests never need Ollama and only exercise the rules."""

import json
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.enums import SaleKind
from app.models.sale import Sale
from app.models.shipment import Shipment
from app.models.user import User
from app.routers.v1 import support
from app.schemas.support import AccionSolicitada, IntencionIAOutput
from app.services import ai_service

URL = "/api/v1/soporte/procesar-reclamo"


def _stub_ia(
    monkeypatch: pytest.MonkeyPatch,
    order_uuid: uuid.UUID | str | None,
    *,
    accion: str = "reembolso",
    confianza: float = 0.95,
) -> None:
    intencion = IntencionIAOutput(
        accion_solicitada=AccionSolicitada(accion), order_uuid=order_uuid, nivel_confianza=confianza
    )

    async def _fake(_mensaje: str) -> IntencionIAOutput:
        return intencion

    monkeypatch.setattr(support, "extraer_intencion", _fake)


async def _order(admin_client: AsyncClient, customer_client: AsyncClient, sku: str, *, deliver: bool) -> str:
    """A paid (or, with deliver=True, delivered) order of 1 unit; returns its id."""
    category = await admin_client.post("/api/v1/categories", json={"name": f"Cat-{sku}"})
    product = await admin_client.post(
        "/api/v1/products",
        json={"sku": sku, "name": sku, "category_id": category.json()["id"], "price": "12000.00"},
    )
    product_id = product.json()["id"]
    await admin_client.post(f"/api/v1/inventory/{product_id}/adjust", json={"delta": 5})
    address = await customer_client.post(
        "/api/v1/customers/me/addresses",
        json={"line1": "Calle 1", "city": "Bogotá", "state": "DC", "postal_code": "110111", "country": "CO"},
    )
    order = await customer_client.post(
        "/api/v1/orders/checkout",
        json={
            "items": [{"product_id": product_id, "quantity": 1}],
            "shipping_address_id": address.json()["id"],
            "method": "card",
        },
    )
    assert order.status_code == 201
    order_id = order.json()["id"]
    if deliver:
        shipment = await admin_client.post(
            f"/api/v1/shipments/order/{order_id}", json={"address_id": address.json()["id"]}
        )
        await admin_client.post(f"/api/v1/shipments/{shipment.json()['id']}/ship")
        delivered = await admin_client.post(f"/api/v1/shipments/{shipment.json()['id']}/deliver")
        assert delivered.status_code == 200
    return order_id


async def test_refund_approved_for_recent_delivery(
    monkeypatch: pytest.MonkeyPatch,
    admin_client: AsyncClient,
    customer_client: AsyncClient,
    customer_user: User,
    db_session: AsyncSession,
) -> None:
    order_id = await _order(admin_client, customer_client, "SUP-001", deliver=True)
    _stub_ia(monkeypatch, order_id)

    resp = await customer_client.post(URL, json={"mensaje": f"me llegó roto!!! pedido {order_id.upper()}"})

    assert resp.status_code == 200
    assert resp.json() == {
        "decision": "aprobado",
        "motivo": "Reembolso aprobado.",
        "order_id": order_id,
        "order_status": "refunded",
    }
    assert (await customer_client.get(f"/api/v1/orders/{order_id}")).json()["status"] == "refunded"
    last = (await admin_client.get(f"/api/v1/orders/{order_id}/history")).json()[-1]
    assert (last["from_status"], last["to_status"], last["source"]) == (
        "delivered",
        "refunded",
        "support_claim",
    )
    assert last["actor"]["email"] == customer_user.email
    amounts = (
        await db_session.execute(select(Sale.kind, Sale.total_amount).where(Sale.order_id == order_id))
    ).all()
    assert sorted((k, str(a)) for k, a in amounts) == [
        (SaleKind.REVERSAL, "-12000.00"),
        (SaleKind.SALE, "12000.00"),
    ]

    # A second claim on the same order finds it already refunded.
    again = await customer_client.post(URL, json={"mensaje": f"otra vez el pedido {order_id}"})
    assert again.json()["decision"] == "rechazado"


async def test_refund_rejected_after_30_days(
    monkeypatch: pytest.MonkeyPatch,
    admin_client: AsyncClient,
    customer_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    order_id = await _order(admin_client, customer_client, "SUP-002", deliver=True)
    await db_session.execute(
        update(Shipment)
        .where(Shipment.order_id == uuid.UUID(order_id))
        .values(delivered_at=datetime.now(UTC) - timedelta(days=31))
    )
    _stub_ia(monkeypatch, order_id)

    resp = await customer_client.post(URL, json={"mensaje": f"quiero mi plata del pedido {order_id}"})

    assert resp.json()["decision"] == "rechazado"
    assert resp.json()["order_status"] == "delivered"


async def test_refund_rejected_when_not_delivered(
    monkeypatch: pytest.MonkeyPatch, admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    order_id = await _order(admin_client, customer_client, "SUP-003", deliver=False)
    _stub_ia(monkeypatch, order_id)

    resp = await customer_client.post(URL, json={"mensaje": f"reembolso del pedido {order_id}"})

    assert resp.json()["decision"] == "rechazado"
    assert resp.json()["order_status"] == "paid"


async def test_someone_elses_order_reads_as_not_found(
    monkeypatch: pytest.MonkeyPatch, admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    order_id = await _order(admin_client, customer_client, "SUP-004", deliver=True)
    _stub_ia(monkeypatch, order_id)

    resp = await admin_client.post(URL, json={"mensaje": f"reembolso del pedido {order_id}"})

    assert resp.json() == {
        "decision": "rechazado",
        "motivo": "Pedido no encontrado.",
        "order_id": None,
        "order_status": None,
    }


@pytest.mark.parametrize(
    ("accion", "confianza", "uuid_in_text"),
    [
        ("estado_pedido", 0.99, True),  # not a refund
        ("reembolso", 0.85, True),  # threshold is strict
        ("reembolso", 0.95, False),  # UUID the LLM made up
    ],
)
async def test_guardrails_send_to_manual_review(
    monkeypatch: pytest.MonkeyPatch,
    admin_client: AsyncClient,
    customer_client: AsyncClient,
    accion: str,
    confianza: float,
    uuid_in_text: bool,
) -> None:
    order_id = await _order(
        admin_client, customer_client, f"SUP-G-{accion}-{confianza}-{uuid_in_text}", deliver=True
    )
    _stub_ia(monkeypatch, order_id, accion=accion, confianza=confianza)
    texto = f"pedido {order_id} llegó mal" if uuid_in_text else "mi pedido llegó mal, devuélvanme"

    resp = await customer_client.post(URL, json={"mensaje": texto})

    assert resp.json()["decision"] == "revision_manual"
    assert (await customer_client.get(f"/api/v1/orders/{order_id}")).json()["status"] == "delivered"


async def test_missing_uuid_or_llm_failure_goes_to_manual_review(
    monkeypatch: pytest.MonkeyPatch, customer_client: AsyncClient
) -> None:
    _stub_ia(monkeypatch, None)
    resp = await customer_client.post(URL, json={"mensaje": "no sé el número, pero quiero reembolso"})
    assert resp.json()["motivo"] == "No se encontró el número de pedido en el mensaje."

    async def _down(_mensaje: str) -> None:
        return None

    monkeypatch.setattr(support, "extraer_intencion", _down)
    resp = await customer_client.post(URL, json={"mensaje": "no sé el número, pero quiero reembolso"})
    assert resp.json()["decision"] == "revision_manual"


async def test_requires_login(client: AsyncClient) -> None:
    resp = await client.post(URL, json={"mensaje": "quiero un reembolso ya"})
    assert resp.status_code == 401


async def test_extraer_intencion_parses_ollama_and_survives_bad_answers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order_id = str(uuid.uuid4())
    valid = {"accion_solicitada": "reembolso", "order_uuid": order_id, "nivel_confianza": 0.9}
    answers = [
        {"message": {"content": json.dumps(valid)}},
        {"message": {"content": '{"accion_solicitada": "regalo", "nivel_confianza": 2}'}},  # fails validation
    ]

    async def _post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
        assert kwargs["json"]["model"] == settings.OLLAMA_MODEL  # type: ignore[index]
        return httpx.Response(200, json=answers.pop(0), request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", _post)

    intencion = await ai_service.extraer_intencion(f"reembolso {order_id}")
    assert intencion == IntencionIAOutput(
        accion_solicitada=AccionSolicitada.REEMBOLSO, order_uuid=uuid.UUID(order_id), nivel_confianza=0.9
    )
    assert await ai_service.extraer_intencion("algo raro") is None


async def test_extraer_intencion_returns_none_when_ollama_is_down(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "OLLAMA_BASE_URL", "http://127.0.0.1:9")  # nothing listens there
    assert await ai_service.extraer_intencion("quiero un reembolso") is None
