"""Writes the database itself rejects (constraints), and how the API reports them."""

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.address import Address
from app.models.enums import ShipmentStatus
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.shipment import Shipment
from app.models.user import User
from app.schemas.order import OrderCreate
from app.scripts.demo_rechazo import demo_rechazo
from app.services.order_service import OrderService
from tests.conftest import test_engine


async def test_foreign_key_violation_returns_409_naming_the_constraint(
    customer_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Skip OrderService's own product check (the friendly 404) so the
    # INSERT reaches PostgreSQL with a product that does not exist.
    async def _create_without_validation(
        self: OrderService, customer_id: uuid.UUID, data: OrderCreate
    ) -> Order:
        order = Order(order_number="ORD-FK-TEST", customer_id=customer_id)
        self.db.add(order)
        await self.db.flush()
        item = data.items[0]
        self.db.add(
            OrderItem(order_id=order.id, product_id=item.product_id, quantity=1, unit_price=1, line_total=1)
        )
        await self.db.flush()
        return order

    monkeypatch.setattr(OrderService, "create_order", _create_without_validation)
    resp = await customer_client.post(
        "/api/v1/orders", json={"items": [{"product_id": str(uuid.uuid4()), "quantity": 1}]}
    )
    assert resp.status_code == 409
    assert "foreign key constraint 'order_items_product_id_fkey'" in resp.json()["detail"]


async def test_check_violation_returns_422_naming_the_constraint(
    customer_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _negative_total(self: OrderService, customer_id: uuid.UUID, data: OrderCreate) -> Order:
        order = Order(order_number="ORD-CK-TEST", customer_id=customer_id, subtotal=-1)
        self.db.add(order)
        await self.db.flush()
        return order

    monkeypatch.setattr(OrderService, "create_order", _negative_total)
    resp = await customer_client.post(
        "/api/v1/orders", json={"items": [{"product_id": str(uuid.uuid4()), "quantity": 1}]}
    )
    assert resp.status_code == 422
    assert "check constraint 'ck_orders_subtotal_non_negative'" in resp.json()["detail"]


@pytest.mark.parametrize(
    ("status", "dates", "constraint"),
    [
        (ShipmentStatus.DELIVERED, ("shipped_at",), "ck_shipments_delivered_has_delivered_at"),
        (ShipmentStatus.IN_TRANSIT, (), "ck_shipments_in_transit_has_shipped_at"),
    ],
)
async def test_shipment_date_checks(
    db_session: AsyncSession,
    customer_user: User,
    status: ShipmentStatus,
    dates: tuple[str, ...],
    constraint: str,
) -> None:
    address = Address(user_id=customer_user.id, line1="x", city="x", state="x", postal_code="1", country="CO")
    order = Order(order_number=f"ORD-{uuid.uuid4().hex[:8]}", customer_id=customer_user.id)
    db_session.add_all([address, order])
    await db_session.flush()

    values = {key: datetime.now(UTC) for key in dates}
    db_session.add(Shipment(order_id=order.id, address_id=address.id, status=status, **values))
    with pytest.raises(IntegrityError) as excinfo:
        await db_session.flush()
    assert excinfo.value.orig.diag.constraint_name == constraint  # type: ignore[union-attr]


async def test_demo_rechazo_reports_the_fk_and_saves_nothing() -> None:
    constraint = await demo_rechazo(async_sessionmaker(test_engine, expire_on_commit=False))
    assert constraint == "order_items_product_id_fkey"
