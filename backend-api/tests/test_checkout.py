from collections.abc import AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.main import app
from app.services.payment_service import ManualPaymentGateway
from tests.test_orders import _make_stocked_product


async def test_checkout_creates_paid_order_with_payment_and_sale(
    admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    product_id = await _make_stocked_product(admin_client, "CHK-001", stock=10, price="25.00")

    resp = await customer_client.post(
        "/api/v1/orders/checkout",
        json={"items": [{"product_id": product_id, "quantity": 2}], "method": "card"},
    )
    assert resp.status_code == 201
    order = resp.json()
    assert order["status"] == "paid"
    assert len(order["items"]) == 1
    assert [(p["status"], p["amount"], p["method"]) for p in order["payments"]] == [
        ("completed", "50.00", "card")
    ]

    inv = (await admin_client.get(f"/api/v1/inventory/{product_id}")).json()
    assert inv["quantity_reserved"] == 2
    summary = (await admin_client.get("/api/v1/reports/summary")).json()
    assert summary["net_revenue"] == "50.00"
    history = (await admin_client.get(f"/api/v1/orders/{order['id']}/history")).json()
    assert [h["source"] for h in history] == ["order_created", "payment"]


async def test_checkout_insufficient_stock_saves_nothing(
    admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    product_id = await _make_stocked_product(admin_client, "CHK-002", stock=1)

    resp = await customer_client.post(
        "/api/v1/orders/checkout", json={"items": [{"product_id": product_id, "quantity": 5}]}
    )
    assert resp.status_code == 409
    assert (await customer_client.get("/api/v1/orders")).json()["total"] == 0


async def test_checkout_rolls_back_everything_if_payment_fails(
    admin_client: AsyncClient,
    customer_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    product_id = await _make_stocked_product(admin_client, "CHK-003", stock=10)

    # The test fixture's get_db never commits or rolls back; this one does
    # what the real get_db does (commit on success, roll back on error),
    # using a savepoint inside the test's transaction.
    async def _get_db_like_production() -> AsyncGenerator[AsyncSession]:
        savepoint = await db_session.begin_nested()
        try:
            yield db_session
        except Exception:
            await savepoint.rollback()
            raise
        else:
            await savepoint.commit()

    app.dependency_overrides[get_db] = _get_db_like_production

    async def _gateway_down(self: ManualPaymentGateway, payment: object) -> None:
        raise RuntimeError("payment gateway down")

    monkeypatch.setattr(ManualPaymentGateway, "charge", _gateway_down)

    with pytest.raises(RuntimeError, match="gateway down"):
        await customer_client.post(
            "/api/v1/orders/checkout", json={"items": [{"product_id": product_id, "quantity": 3}]}
        )

    # The order and its stock reservation were already flushed when the
    # payment failed: the rollback removed them too.
    assert (await customer_client.get("/api/v1/orders")).json()["total"] == 0
    inv = (await admin_client.get(f"/api/v1/inventory/{product_id}")).json()
    assert inv["quantity_reserved"] == 0


async def test_order_out_includes_payments(admin_client: AsyncClient, customer_client: AsyncClient) -> None:
    product_id = await _make_stocked_product(admin_client, "CHK-004", stock=10, price="10.00")
    order = (
        await customer_client.post(
            "/api/v1/orders", json={"items": [{"product_id": product_id, "quantity": 1}]}
        )
    ).json()
    assert order["payments"] == []

    await customer_client.post("/api/v1/payments", json={"order_id": order["id"], "method": "cash"})

    detail = (await customer_client.get(f"/api/v1/orders/{order['id']}")).json()
    assert [(p["status"], p["amount"], p["method"]) for p in detail["payments"]] == [
        ("completed", "10.00", "cash")
    ]
    listed = (await admin_client.get("/api/v1/orders")).json()["items"]
    assert [len(o["payments"]) for o in listed] == [1]
