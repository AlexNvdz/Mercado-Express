"""Admin panel reads: search/date filters, product fields in order items and
inventory rows, and the cached report summary."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.enums import UserRole
from app.models.order import Order
from app.services import report_service
from tests.conftest import _authed_client, _create_user
from tests.test_orders import _make_stocked_product


async def _order(client: AsyncClient, product_id: str) -> dict:
    resp = await client.post("/api/v1/orders", json={"items": [{"product_id": product_id, "quantity": 1}]})
    assert resp.status_code == 201
    return resp.json()


async def _numbers(admin_client: AsyncClient, **params: str) -> set[str]:
    resp = await admin_client.get("/api/v1/orders", params=params)
    assert resp.status_code == 200
    assert resp.json()["total"] == len(resp.json()["items"])
    return {o["order_number"] for o in resp.json()["items"]}


async def test_orders_search_by_number_email_and_name_combined_with_status(
    db_session: AsyncSession, admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    product_id = await _make_stocked_product(admin_client, "SRCH-001", stock=10)
    first = await _order(customer_client, product_id)
    second = await _order(customer_client, product_id)
    ana = await _create_user(db_session, email="ana.perez@example.com", role=UserRole.CUSTOMER)
    ana.full_name = "Ana Pérez"
    async with _authed_client(ana) as ana_client:
        anas = await _order(ana_client, product_id)

    assert await _numbers(admin_client, search=first["order_number"][4:].lower()) == {first["order_number"]}
    assert await _numbers(admin_client, search="ANA.PEREZ@") == {anas["order_number"]}
    assert await _numbers(admin_client, search="ana pé") == {anas["order_number"]}
    customer_orders = {first["order_number"], second["order_number"]}
    assert await _numbers(admin_client, search="customer-") == customer_orders

    await customer_client.post("/api/v1/payments", json={"order_id": second["id"]})
    assert await _numbers(admin_client, search="customer-", status="paid") == {second["order_number"]}
    # A customer's search never reaches other customers' orders.
    resp = await customer_client.get("/api/v1/orders", params={"search": "ana"})
    assert resp.json()["total"] == 0


async def test_orders_created_date_range_is_inclusive_utc(
    db_session: AsyncSession, admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    product_id = await _make_stocked_product(admin_client, "SRCH-002", stock=10)
    old = await _order(customer_client, product_id)
    new = await _order(customer_client, product_id)
    await db_session.execute(
        update(Order)
        .where(Order.id == old["id"])
        .values(created_at=datetime(2020, 1, 15, 23, 59, tzinfo=UTC))
    )

    day = {"created_from": "2020-01-15", "created_to": "2020-01-15"}
    assert await _numbers(admin_client, **day) == {old["order_number"]}
    assert await _numbers(admin_client, created_to="2020-01-14") == set()
    assert await _numbers(admin_client, created_from="2020-01-16") == {new["order_number"]}
    resp = await admin_client.get("/api/v1/orders", params={"created_from": "15/01/2020"})
    assert resp.status_code == 422


async def test_customers_search_by_name_email_or_phone(
    db_session: AsyncSession, admin_client: AsyncClient
) -> None:
    luis = await _create_user(db_session, email="luis.gomez@example.com", role=UserRole.CUSTOMER)
    luis.full_name, luis.phone = "Luis Gómez", "+57 300 555 1234"
    await _create_user(db_session, email="otra@example.com", role=UserRole.CUSTOMER)
    await db_session.flush()

    async def emails(search: str) -> list[str]:
        resp = await admin_client.get("/api/v1/customers", params={"search": search})
        assert resp.status_code == 200
        return [c["email"] for c in resp.json()["items"]]

    assert await emails("GÓMEZ") == ["luis.gomez@example.com"]
    assert await emails("luis.gomez@") == ["luis.gomez@example.com"]
    assert await emails("555 1234") == ["luis.gomez@example.com"]
    assert await emails("nadie") == []


async def test_order_items_carry_product_name_and_sku(
    admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    product_id = await _make_stocked_product(admin_client, "SRCH-003", stock=10)
    order = await _order(customer_client, product_id)
    assert [(i["product_name"], i["product_sku"]) for i in order["items"]] == [
        ("Product SRCH-003", "SRCH-003")
    ]

    detail = (await admin_client.get(f"/api/v1/orders/{order['id']}")).json()
    assert detail["items"][0]["product_name"] == "Product SRCH-003"
    listed = (await admin_client.get("/api/v1/orders")).json()["items"]
    assert listed[0]["items"][0]["product_sku"] == "SRCH-003"
    # Status changes return the order too (they refresh it after the update).
    cancelled = (await customer_client.post(f"/api/v1/orders/{order['id']}/cancel")).json()
    assert cancelled["items"][0]["product_sku"] == "SRCH-003"


async def test_inventory_items_carry_product_fields_and_search(admin_client: AsyncClient) -> None:
    active = await _make_stocked_product(admin_client, "SRCH-INV-1", stock=3)
    inactive = await _make_stocked_product(admin_client, "SRCH-INV-2", stock=3)
    await admin_client.patch(f"/api/v1/products/{inactive}", json={"is_active": False})

    resp = await admin_client.get("/api/v1/inventory", params={"include_inactive": "true"})
    rows = {
        r["product_id"]: (r["product_name"], r["product_sku"], r["product_is_active"])
        for r in resp.json()["items"]
    }
    assert rows == {
        active: ("Product SRCH-INV-1", "SRCH-INV-1", True),
        inactive: ("Product SRCH-INV-2", "SRCH-INV-2", False),
    }

    resp = await admin_client.get("/api/v1/inventory", params={"search": "inv-2", "include_inactive": "true"})
    assert [r["product_id"] for r in resp.json()["items"]] == [inactive]
    resp = await admin_client.get("/api/v1/inventory", params={"search": "product srch"})
    assert [r["product_id"] for r in resp.json()["items"]] == [active]  # inactive left out by default


async def test_report_summary_is_cached_for_report_cache_seconds(
    admin_client: AsyncClient, customer_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(report_service, "_cache", {})
    monkeypatch.setattr(settings, "REPORT_CACHE_SECONDS", 60)
    product_id = await _make_stocked_product(admin_client, "SRCH-RPT", stock=10, price="10.00")

    before = (await admin_client.get("/api/v1/reports/summary")).json()
    await customer_client.post(
        "/api/v1/orders/checkout", json={"items": [{"product_id": product_id, "quantity": 1}]}
    )
    cached = (await admin_client.get("/api/v1/reports/summary")).json()
    assert cached == before  # same generated_at, the new sale not in yet

    monkeypatch.setattr(settings, "REPORT_CACHE_SECONDS", 0)
    fresh = (await admin_client.get("/api/v1/reports/summary")).json()
    assert fresh["net_revenue"] == "10.00"
    assert fresh["generated_at"] > before["generated_at"]
