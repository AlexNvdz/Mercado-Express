"""Minimum product price (MIN_PRODUCT_PRICE) and no zero-value purchases."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.product import Product
from app.models.user import User

pytestmark = pytest.mark.asyncio


async def _make_stocked_product(admin_client: AsyncClient, sku: str) -> str:
    category = await admin_client.post("/api/v1/categories", json={"name": f"Cat {sku}"})
    product = await admin_client.post(
        "/api/v1/products",
        json={"sku": sku, "name": sku, "category_id": category.json()["id"], "price": "5900.00"},
    )
    assert product.status_code == 201
    await admin_client.post(f"/api/v1/inventory/{product.json()['id']}/adjust", json={"delta": 10})
    return product.json()["id"]


@pytest.mark.parametrize(("price", "expected"), [("0", 422), ("5899.99", 422), ("5900.00", 201)])
async def test_create_product_enforces_minimum_price(
    admin_client: AsyncClient, price: str, expected: int
) -> None:
    category = await admin_client.post("/api/v1/categories", json={"name": "Min"})
    resp = await admin_client.post(
        "/api/v1/products",
        json={"sku": "MIN-001", "name": "x", "category_id": category.json()["id"], "price": price},
    )
    assert resp.status_code == expected


async def test_update_product_rejects_price_below_minimum(admin_client: AsyncClient) -> None:
    product_id = await _make_stocked_product(admin_client, "MIN-UPD")
    resp = await admin_client.patch(f"/api/v1/products/{product_id}", json={"price": "0"})
    assert resp.status_code == 422


@pytest.mark.parametrize("path", ["/api/v1/orders", "/api/v1/orders/checkout"])
async def test_order_rejects_product_priced_below_minimum(
    admin_client: AsyncClient, customer_client: AsyncClient, db_session: AsyncSession, path: str
) -> None:
    # A row priced before the minimum existed: the API can no longer write it.
    product_id = await _make_stocked_product(admin_client, "MIN-OLD")
    await db_session.execute(update(Product).where(Product.id == uuid.UUID(product_id)).values(price=0))

    resp = await customer_client.post(path, json={"items": [{"product_id": product_id, "quantity": 1}]})
    assert resp.status_code == 422
    inventory = await admin_client.get(f"/api/v1/inventory/{product_id}")
    assert inventory.json()["quantity_reserved"] == 0


async def test_zero_total_order_cannot_be_paid(
    customer_client: AsyncClient, customer_user: User, db_session: AsyncSession
) -> None:
    order = Order(order_number="ORD-ZERO", customer_id=customer_user.id, total_amount=0)
    db_session.add(order)
    await db_session.flush()

    resp = await customer_client.post("/api/v1/payments", json={"order_id": str(order.id), "method": "card"})
    assert resp.status_code == 422
