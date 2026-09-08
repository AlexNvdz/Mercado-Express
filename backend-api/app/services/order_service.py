"""Order orchestration: validate products -> reserve inventory -> compute
totals -> persist order + items.

Flow modeled after the architecture doc:
  cliente -> creacion del pedido -> validacion de productos ->
  validacion/reserva de inventario -> calculo de totales -> pago ->
  preparacion -> despacho -> entrega

Payment, preparation, dispatch and delivery are separate services/routers
(payments, shipments) that advance `Order.status` from here on.
"""

import secrets
import uuid
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.exceptions import InvalidStateTransitionError, NotFoundError, ValidationAppError
from app.models.enums import OrderStatus
from app.models.order import Order
from app.models.order_item import OrderItem
from app.repositories.address_repository import AddressRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.order import OrderCreate

# Allowed forward transitions. Cancellation is allowed from any pre-shipment
# state; terminal states have no outgoing edges.
_ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.AWAITING_PAYMENT, OrderStatus.CANCELLED},
    OrderStatus.AWAITING_PAYMENT: {OrderStatus.PAID, OrderStatus.CANCELLED},
    OrderStatus.PAID: {OrderStatus.PREPARING, OrderStatus.CANCELLED, OrderStatus.REFUNDED},
    OrderStatus.PREPARING: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
    OrderStatus.REFUNDED: set(),
}

_TWO_PLACES = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


def _generate_order_number() -> str:
    return f"ORD-{secrets.token_hex(5).upper()}"


class OrderService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.orders = OrderRepository(db)
        self.products = ProductRepository(db)
        self.inventory = InventoryRepository(db)
        self.addresses = AddressRepository(db)

    async def create_order(self, customer_id: uuid.UUID, data: OrderCreate) -> Order:
        if data.shipping_address_id is not None:
            address = await self.addresses.get(data.shipping_address_id)
            if address is None or address.user_id != customer_id:
                raise NotFoundError("Shipping address not found for this customer.")

        # 1. Validate products (exist, active) and snapshot prices.
        line_items: list[dict[str, Any]] = []
        subtotal = Decimal("0")
        for requested_item in data.items:
            product = await self.products.get(requested_item.product_id)
            if product is None or not product.is_active:
                raise NotFoundError(f"Product {requested_item.product_id} not found or inactive.")
            unit_price = Decimal(str(product.price))
            line_total = _money(unit_price * requested_item.quantity)
            subtotal += line_total
            line_items.append(
                {
                    "product_id": product.id,
                    "quantity": requested_item.quantity,
                    "unit_price": unit_price,
                    "line_total": line_total,
                }
            )

        # 2. Reserve inventory for every line (raises InsufficientStockError,
        #    which rolls back the whole transaction via get_db's exception path).
        for line_item in line_items:
            await self.inventory.reserve(line_item["product_id"], line_item["quantity"])

        # 3. Compute totals.
        subtotal = _money(subtotal)
        tax_amount = _money(subtotal * Decimal(str(settings.TAX_RATE)))
        shipping_amount = _money(Decimal(str(settings.FLAT_SHIPPING_FEE)))
        total_amount = _money(subtotal + tax_amount + shipping_amount)

        order = Order(
            order_number=_generate_order_number(),
            customer_id=customer_id,
            status=OrderStatus.PENDING,
            subtotal=subtotal,
            tax_amount=tax_amount,
            shipping_amount=shipping_amount,
            total_amount=total_amount,
            shipping_address_id=data.shipping_address_id,
            notes=data.notes,
        )
        self.db.add(order)
        await self.db.flush()

        for line_item in line_items:
            self.db.add(OrderItem(order_id=order.id, **line_item))

        await self.db.flush()
        loaded = await self.orders.get_with_items(order.id)
        assert loaded is not None
        return loaded

    async def get(self, order_id: uuid.UUID) -> Order:
        order = await self.orders.get_with_items(order_id)
        if order is None:
            raise NotFoundError(f"Order {order_id} not found.")
        return order

    async def get_for_customer(self, order_id: uuid.UUID, customer_id: uuid.UUID) -> Order:
        order = await self.get(order_id)
        if order.customer_id != customer_id:
            raise NotFoundError(f"Order {order_id} not found.")
        return order

    async def list_for_customer(
        self, customer_id: uuid.UUID, *, offset: int, limit: int
    ) -> tuple[list[Order], int]:
        items = await self.orders.list_for_customer(customer_id, offset=offset, limit=limit)
        total = await self.orders.count(filters=[Order.customer_id == customer_id])
        return items, total

    async def list_all(self, *, offset: int, limit: int) -> tuple[list[Order], int]:
        items = await self.orders.list(offset=offset, limit=limit, order_by=Order.created_at.desc())
        total = await self.orders.count()
        return items, total

    async def transition_status(self, order_id: uuid.UUID, new_status: OrderStatus) -> Order:
        order = await self.get(order_id)
        allowed = _ALLOWED_TRANSITIONS.get(order.status, set())
        if new_status not in allowed:
            raise InvalidStateTransitionError(
                f"Cannot transition order from '{order.status}' to '{new_status}'."
            )

        if new_status == OrderStatus.CANCELLED:
            for item in order.items:
                await self.inventory.release(item.product_id, item.quantity)

        order.status = new_status
        await self.db.flush()
        # `updated_at` has onupdate=func.now(): the column is left expired
        # after flush, and this object is handed straight back to a Pydantic
        # response model without another query -- refresh so that read
        # happens here (inside an awaited call) rather than as an implicit
        # lazy-load later (which would raise MissingGreenlet).
        await self.db.refresh(order)
        return order

    async def cancel(self, order_id: uuid.UUID, customer_id: uuid.UUID | None = None) -> Order:
        order = await self.get(order_id)
        if customer_id is not None and order.customer_id != customer_id:
            raise NotFoundError(f"Order {order_id} not found.")
        if order.status not in (OrderStatus.PENDING, OrderStatus.AWAITING_PAYMENT):
            raise ValidationAppError(
                f"Order in status '{order.status}' can no longer be cancelled by the customer."
            )
        return await self.transition_status(order_id, OrderStatus.CANCELLED)
