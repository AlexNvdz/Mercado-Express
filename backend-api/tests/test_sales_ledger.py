import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SaleKind
from app.models.sale import Sale
from app.services.order_service import OrderService


async def _paid_order(admin_client: AsyncClient, customer_client: AsyncClient, sku: str, price: str) -> str:
    category = await admin_client.post("/api/v1/categories", json={"name": f"Cat-{sku}"})
    product = await admin_client.post(
        "/api/v1/products",
        json={"sku": sku, "name": f"Product {sku}", "category_id": category.json()["id"], "price": price},
    )
    product_id = product.json()["id"]
    await admin_client.post(f"/api/v1/inventory/{product_id}/adjust", json={"delta": 5})
    order = await customer_client.post(
        "/api/v1/orders", json={"items": [{"product_id": product_id, "quantity": 1}]}
    )
    order_id = order.json()["id"]
    paid = await customer_client.post("/api/v1/payments", json={"order_id": order_id, "method": "card"})
    assert paid.status_code == 201
    return order_id


async def _entries(db_session: AsyncSession, order_id: str) -> list[tuple[SaleKind, Decimal]]:
    result = await db_session.execute(
        select(Sale.kind, Sale.total_amount).where(Sale.order_id == uuid.UUID(order_id)).order_by(Sale.kind)
    )
    return [(kind, Decimal(amount)) for kind, amount in result.all()]


@pytest.mark.parametrize("target", ["cancelled", "refunded"])
async def test_cancel_or_refund_of_paid_order_appends_reversal(
    admin_client: AsyncClient, customer_client: AsyncClient, db_session: AsyncSession, target: str
) -> None:
    order_id = await _paid_order(admin_client, customer_client, f"LED-{target}", "40.00")
    assert await _entries(db_session, order_id) == [(SaleKind.SALE, Decimal("40.00"))]

    resp = await admin_client.patch(f"/api/v1/orders/{order_id}/status", json={"status": target})
    assert resp.status_code == 200

    # The original sale is untouched; the reversal is its negation.
    assert await _entries(db_session, order_id) == [
        (SaleKind.SALE, Decimal("40.00")),
        (SaleKind.REVERSAL, Decimal("-40.00")),
    ]


async def test_cancelling_unpaid_order_writes_no_ledger_entry(
    admin_client: AsyncClient, customer_client: AsyncClient, db_session: AsyncSession
) -> None:
    category = await admin_client.post("/api/v1/categories", json={"name": "Cat-LED-unpaid"})
    product = await admin_client.post(
        "/api/v1/products",
        json={"sku": "LED-UNPAID", "name": "Unpaid", "category_id": category.json()["id"], "price": "9.00"},
    )
    await admin_client.post(f"/api/v1/inventory/{product.json()['id']}/adjust", json={"delta": 5})
    order = await customer_client.post(
        "/api/v1/orders", json={"items": [{"product_id": product.json()["id"], "quantity": 1}]}
    )
    order_id = order.json()["id"]

    resp = await customer_client.post(f"/api/v1/orders/{order_id}/cancel")
    assert resp.status_code == 200
    assert await _entries(db_session, order_id) == []


async def test_record_reversal_is_idempotent(
    admin_client: AsyncClient, customer_client: AsyncClient, db_session: AsyncSession
) -> None:
    order_id = await _paid_order(admin_client, customer_client, "LED-IDEM", "15.00")
    await admin_client.patch(f"/api/v1/orders/{order_id}/status", json={"status": "refunded"})

    service = OrderService(db_session)
    order = await service.get(uuid.UUID(order_id))
    first = await service.record_reversal(order)
    second = await service.record_reversal(order)

    assert first is not None and second is not None
    assert first.id == second.id
    kinds = [kind for kind, _ in await _entries(db_session, order_id)]
    assert kinds == [SaleKind.SALE, SaleKind.REVERSAL]


async def test_database_rejects_second_reversal_and_wrong_sign(
    admin_client: AsyncClient, customer_client: AsyncClient, db_session: AsyncSession
) -> None:
    order_id = uuid.UUID(await _paid_order(admin_client, customer_client, "LED-DB", "10.00"))
    await admin_client.patch(f"/api/v1/orders/{order_id}/status", json={"status": "cancelled"})

    bad_rows = [
        Sale(order_id=order_id, kind=SaleKind.REVERSAL, total_amount=Decimal("-10.00")),  # duplicate
        Sale(order_id=order_id, kind=SaleKind.SALE, total_amount=Decimal("10.00")),  # duplicate
    ]
    other_order_id = uuid.UUID(await _paid_order(admin_client, customer_client, "LED-DB2", "10.00"))
    bad_rows.append(Sale(order_id=other_order_id, kind=SaleKind.REVERSAL, total_amount=Decimal("5.00")))

    for row in bad_rows:
        with pytest.raises(IntegrityError):
            async with db_session.begin_nested():
                db_session.add(row)
                await db_session.flush()
