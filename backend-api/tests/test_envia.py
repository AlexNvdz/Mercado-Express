"""Envia.com integration with a fake Envia (httpx.MockTransport): address
validation, locations, automatic/panel labels, tracking sync, voiding."""

import json
import uuid
from collections.abc import Generator
from typing import Any

import httpx
import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.services import envia_client, shipment_service
from tests.conftest import fake_geocodes
from tests.test_shipments import _inventory, _make_stocked_product

ADDRESS = {"line1": "Carrera 43A # 1-50", "city": "Medellín", "state": "Antioquia", "country": "CO"}


class FakeEnvia:
    """Shipping API stand-in: carrier "barato" quotes two door services plus
    a cheaper cash-on-delivery and to-office one (never picked), "caro" one;
    every call is recorded."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.track_status = "Created"
        self.rate_error = False

    def __call__(self, request: httpx.Request) -> httpx.Response:
        geo = fake_geocodes(request)
        if geo is not None:
            return geo
        body = json.loads(request.content)
        path = request.url.path
        self.calls.append((path, body))
        assert request.headers["Authorization"] == "Bearer test-key"
        if path == "/ship/rate/":
            if self.rate_error:
                return httpx.Response(200, json={"meta": "error", "error": {"message": "Sin cobertura"}})
            prices = {
                "barato": [("ground", 12000), ("express", 9000), ("express_cod", 100), ("mensajeria_do", 50)],
                "caro": [("ground", 30000)],
            }
            carrier = body["shipment"]["carrier"]
            data = [{"carrier": carrier, "service": s, "totalPrice": p} for s, p in prices[carrier]]
            return httpx.Response(200, json={"meta": "rate", "data": data})
        if path == "/ship/generate/":
            shipment = body["shipment"]
            label = {
                "carrier": shipment["carrier"],
                "service": shipment["service"],
                "trackingNumber": "ENV-123",
                "trackUrl": "https://envia.com/rastreo?label=ENV-123",
                "label": "https://labels.example/ENV-123.pdf",
                "totalPrice": 9000,
            }
            return httpx.Response(200, json={"meta": "generate", "data": [label]})
        if path == "/ship/generaltrack/":
            return httpx.Response(200, json={"meta": "generaltrack", "data": [{"status": self.track_status}]})
        if path == "/ship/cancel/":
            return httpx.Response(200, json={"meta": "cancel", "data": [{"balanceReturned": 1}]})
        return httpx.Response(404, text="not found")

    def paths(self) -> list[str]:
        return [path for path, _ in self.calls]


@pytest.fixture
def envia() -> Generator[FakeEnvia]:
    """Labels on, against the fake. Turn it on only after paying in a test:
    with a key, POST /payments schedules the real background task."""
    fake = FakeEnvia()
    envia_client.transport = httpx.MockTransport(fake)
    original = settings.ENVIA_CARRIERS
    settings.ENVIA_CARRIERS = ["caro", "barato"]
    yield fake
    settings.ENVIA_CARRIERS = original


def _labels_on() -> None:
    settings.ENVIA_API_KEY = "test-key"


async def _paid_order(
    admin_client: AsyncClient, customer_client: AsyncClient, sku: str, **address: str
) -> str:
    product_id = await _make_stocked_product(admin_client, sku, stock=10)
    addr = await customer_client.post("/api/v1/customers/me/addresses", json={**ADDRESS, **address})
    assert addr.status_code == 201, addr.text
    order = await customer_client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": product_id, "quantity": 2}], "shipping_address_id": addr.json()["id"]},
    )
    order_id: str = order.json()["id"]
    paid = await customer_client.post("/api/v1/payments", json={"order_id": order_id, "method": "card"})
    assert paid.status_code == 201
    return order_id


async def test_colombian_address_gets_postal_code_and_unknown_city_is_rejected(
    customer_client: AsyncClient,
) -> None:
    resp = await customer_client.post(
        "/api/v1/customers/me/addresses", json={**ADDRESS, "phone": "3001112233"}
    )
    assert resp.status_code == 201
    assert resp.json()["postal_code"] == "050001"
    assert resp.json()["phone"] == "3001112233"

    bad = await customer_client.post("/api/v1/customers/me/addresses", json={**ADDRESS, "city": "NoExiste"})
    assert bad.status_code == 422
    unknown_state = await customer_client.post(
        "/api/v1/customers/me/addresses", json={**ADDRESS, "state": "Narnia"}
    )
    assert unknown_state.status_code == 422

    abroad = {"line1": "Main St", "city": "Springfield", "state": "IL", "country": "US"}
    assert (await customer_client.post("/api/v1/customers/me/addresses", json=abroad)).status_code == 422

    moved = await customer_client.patch(
        f"/api/v1/customers/me/addresses/{resp.json()['id']}", json={"city": "NoExiste"}
    )
    assert moved.status_code == 422


async def test_locations(client: AsyncClient) -> None:
    states = (await client.get("/api/v1/locations/co/states")).json()
    assert len(states) == 33
    assert {"code": "CN", "name": "Cundinamarca"} in states
    cities = await client.get("/api/v1/locations/co/states/antioquia/cities")
    assert cities.json() == ["Abejorral", "Envigado", "Medellín"]
    assert (await client.get("/api/v1/locations/co/states/XX/cities")).status_code == 404


async def test_envia_label_buys_the_cheapest_service(
    admin_client: AsyncClient, customer_client: AsyncClient, envia: FakeEnvia
) -> None:
    order_id = await _paid_order(admin_client, customer_client, "ENV-001", phone="3001112233")
    _labels_on()

    resp = await admin_client.post(f"/api/v1/shipments/order/{order_id}/envia")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert (body["status"], body["carrier"], body["service"]) == ("preparing", "barato", "express")
    assert body["tracking_number"] == "ENV-123"
    assert body["label_url"] == "https://labels.example/ENV-123.pdf"
    assert body["shipping_cost"] == "9000.00"
    assert envia.paths() == ["/ship/rate/", "/ship/rate/", "/ship/generate/"]
    generated = envia.calls[-1][1]
    assert generated["destination"]["city"] == "05001000"  # DANE, not the name
    assert generated["destination"]["phone"] == "3001112233"
    assert (generated["destination"]["street"], generated["destination"]["number"]) == ("Carrera 43A", "1-50")
    assert (await admin_client.get(f"/api/v1/orders/{order_id}")).json()["status"] == "preparing"

    # The customer sees how to track it, not the label nor what it cost.
    mine = (await customer_client.get(f"/api/v1/shipments/order/{order_id}")).json()
    assert mine["tracking_url"] == "https://envia.com/rastreo?label=ENV-123"
    assert mine["label_url"] is None and mine["shipping_cost"] is None

    edit = await admin_client.patch(f"/api/v1/shipments/{body['id']}", json={"tracking_number": "X"})
    assert edit.status_code == 409
    again = await admin_client.post(f"/api/v1/shipments/order/{order_id}/envia")
    assert again.status_code == 409


async def test_envia_label_failures_leave_the_order_paid(
    admin_client: AsyncClient, customer_client: AsyncClient, envia: FakeEnvia
) -> None:
    no_phone = await _paid_order(admin_client, customer_client, "ENV-002")
    _labels_on()
    resp = await admin_client.post(f"/api/v1/shipments/order/{no_phone}/envia")
    assert resp.status_code == 422
    assert "teléfono" in resp.json()["detail"]

    settings.ENVIA_API_KEY = None
    order_id = await _paid_order(admin_client, customer_client, "ENV-003", phone="3001112233")
    _labels_on()
    envia.rate_error = True
    resp = await admin_client.post(f"/api/v1/shipments/order/{order_id}/envia")
    assert resp.status_code == 502
    assert "Sin cobertura" in resp.json()["detail"]
    assert (await admin_client.get(f"/api/v1/orders/{order_id}")).json()["status"] == "paid"
    assert (await admin_client.get(f"/api/v1/shipments/order/{order_id}")).status_code == 404


async def test_sync_follows_the_carrier(
    admin_client: AsyncClient, customer_client: AsyncClient, envia: FakeEnvia
) -> None:
    order_id = await _paid_order(admin_client, customer_client, "ENV-004", phone="3001112233")
    _labels_on()
    shipment_id = (await admin_client.post(f"/api/v1/shipments/order/{order_id}/envia")).json()["id"]
    product_id = (await admin_client.get(f"/api/v1/orders/{order_id}")).json()["items"][0]["product_id"]

    created = (await admin_client.post(f"/api/v1/shipments/{shipment_id}/sync")).json()
    assert (created["carrier_status"], created["status"]) == ("Created", "preparing")

    envia.track_status = "Picked Up"
    picked = (await admin_client.post(f"/api/v1/shipments/{shipment_id}/sync")).json()
    assert picked["status"] == "in_transit"
    assert await _inventory(admin_client, product_id) == (8, 0)

    envia.track_status = "Delivered"
    delivered = (await admin_client.post(f"/api/v1/shipments/{shipment_id}/sync")).json()
    assert delivered["status"] == "delivered"
    history = (await admin_client.get(f"/api/v1/orders/{order_id}/history")).json()
    assert [h["to_status"] for h in history][-3:] == ["preparing", "shipped", "delivered"]


async def test_sync_requires_an_envia_label(admin_client: AsyncClient, customer_client: AsyncClient) -> None:
    order_id = await _paid_order(admin_client, customer_client, "ENV-005")
    address_id = (await admin_client.get(f"/api/v1/orders/{order_id}")).json()["shipping_address_id"]
    manual = await admin_client.post(f"/api/v1/shipments/order/{order_id}", json={"address_id": address_id})
    resp = await admin_client.post(f"/api/v1/shipments/{manual.json()['id']}/sync")
    assert resp.status_code == 422


async def test_cancelling_the_order_voids_its_label(
    admin_client: AsyncClient, customer_client: AsyncClient, envia: FakeEnvia
) -> None:
    order_id = await _paid_order(admin_client, customer_client, "ENV-006", phone="3001112233")
    _labels_on()
    await admin_client.post(f"/api/v1/shipments/order/{order_id}/envia")

    resp = await admin_client.patch(f"/api/v1/orders/{order_id}/status", json={"status": "cancelled"})
    assert resp.status_code == 200
    assert envia.calls[-1] == ("/ship/cancel/", {"carrier": "barato", "trackingNumber": "ENV-123"})


async def test_checkout_schedules_the_automatic_label(
    admin_client: AsyncClient, customer_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    product_id = await _make_stocked_product(admin_client, "ENV-007", stock=10)
    scheduled: list[uuid.UUID] = []

    async def record(order_id: uuid.UUID) -> None:
        scheduled.append(order_id)

    monkeypatch.setattr(shipment_service, "auto_create_envia_shipment", record)
    _labels_on()
    resp = await customer_client.post(
        "/api/v1/orders/checkout",
        json={"items": [{"product_id": product_id, "quantity": 1}], "method": "card"},
    )
    assert resp.status_code == 201
    assert scheduled == [uuid.UUID(resp.json()["id"])]
