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
from collections.abc import Collection
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.exceptions import InvalidStateTransitionError, NotFoundError, ValidationAppError
from app.models.enums import OrderStatus, OrderStatusChangeSource, SaleKind, ShipmentStatus
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.order_status_change import OrderStatusChange
from app.models.sale import Sale
from app.repositories.address_repository import AddressRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.order_status_change_repository import OrderStatusChangeRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.sale_repository import SaleRepository
from app.repositories.shipment_repository import ShipmentRepository
from app.schemas.order import OrderCreate

# Manual-override targets for PATCH /orders/{id}/status (staff corrections).
# The normal flow is driven by other resources: PaymentService moves
# `pending -> paid`, ShipmentService moves `paid -> preparing` (shipment
# created), `-> shipped` (dispatched) and `-> delivered`. Absent on purpose:
# - `pending -> paid`: it would mark an order paid with no payment and no Sale.
# - `-> shipped` / `-> delivered`: only the order's shipment may move it
#   there, so an order is never shipped without a shipment and tracking
#   number, and its stock is fulfilled exactly once (on dispatch).
# Cancellation/refund are only reachable before dispatch; terminal states
# have no outgoing edges.
_ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.CANCELLED},
    OrderStatus.PAID: {OrderStatus.PREPARING, OrderStatus.CANCELLED, OrderStatus.REFUNDED},
    OrderStatus.PREPARING: {OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: set(),
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
    OrderStatus.REFUNDED: set(),
}

_UNDISPATCHED_SHIPMENT_STATUSES = {ShipmentStatus.PENDING, ShipmentStatus.PREPARING}

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
        self.sales = SaleRepository(db)
        self.shipments = ShipmentRepository(db)
        self.status_changes = OrderStatusChangeRepository(db)

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

        await self.status_changes.record(
            order_id=order.id,
            from_status=None,
            to_status=OrderStatus.PENDING,
            source=OrderStatusChangeSource.ORDER_CREATED,
            actor_id=customer_id,
        )
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

    async def list_orders(
        self,
        *,
        customer_id: uuid.UUID | None,
        statuses: Collection[OrderStatus] | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Order], int]:
        """`customer_id=None` lists every customer's orders (staff); an empty
        or None `statuses` means any status. `total` counts the same filters."""
        filters: list[Any] = []
        if customer_id is not None:
            filters.append(Order.customer_id == customer_id)
        if statuses:
            filters.append(Order.status.in_(set(statuses)))
        items = await self.orders.list_filtered(filters=filters, offset=offset, limit=limit)
        total = await self.orders.count(filters=filters)
        return items, total

    async def history(self, order_id: uuid.UUID) -> list[OrderStatusChange]:
        if await self.orders.get(order_id) is None:
            raise NotFoundError(f"Order {order_id} not found.")
        return await self.status_changes.list_for_order(order_id)

    async def _get_locked(self, order_id: uuid.UUID) -> Order:
        order = await self.orders.get_with_items(order_id, for_update=True)
        if order is None:
            raise NotFoundError(f"Order {order_id} not found.")
        return order

    async def transition_status(
        self,
        order_id: uuid.UUID,
        new_status: OrderStatus,
        *,
        actor_id: uuid.UUID | None,
        source: OrderStatusChangeSource = OrderStatusChangeSource.MANUAL,
    ) -> Order:
        order = await self._get_locked(order_id)
        allowed = _ALLOWED_TRANSITIONS.get(order.status, set())
        if new_status not in allowed:
            raise InvalidStateTransitionError(
                f"Cannot transition order from '{order.status}' to '{new_status}'."
            )

        if new_status in (OrderStatus.CANCELLED, OrderStatus.REFUNDED):
            # Both are only reachable before dispatch (see _ALLOWED_TRANSITIONS),
            # so the stock is still reserved, never fulfilled: release it.
            for item in order.items:
                await self.inventory.release(item.product_id, item.quantity)
            await self.record_reversal(order)
            shipment = await self.shipments.get_by_order_id(order.id)
            if shipment is not None and shipment.status in _UNDISPATCHED_SHIPMENT_STATUSES:
                shipment.status = ShipmentStatus.CANCELLED

        await self.status_changes.record(
            order_id=order.id,
            from_status=order.status,
            to_status=new_status,
            source=source,
            actor_id=actor_id,
        )
        order.status = new_status
        await self.db.flush()
        # `updated_at` has onupdate=func.now(): the column is left expired
        # after flush, and this object is handed straight back to a Pydantic
        # response model without another query -- refresh so that read
        # happens here (inside an awaited call) rather than as an implicit
        # lazy-load later (which would raise MissingGreenlet).
        await self.db.refresh(order)
        return order

    async def record_reversal(self, order: Order) -> Sale | None:
        """Append the negative ledger entry for a paid order that is being
        cancelled or refunded; the original `sale` entry is never touched.

        Idempotent: returns None if the order was never paid (no `sale`
        entry), and the existing reversal if there is one already. The
        unique (order_id, kind) constraint backs this up in the database.
        """
        sale = await self.sales.get_for_order(order.id, SaleKind.SALE)
        if sale is None:
            return None
        existing = await self.sales.get_for_order(order.id, SaleKind.REVERSAL)
        if existing is not None:
            return existing
        return await self.sales.create(
            {"order_id": order.id, "kind": SaleKind.REVERSAL, "total_amount": -sale.total_amount}
        )

    async def cancel(
        self, order_id: uuid.UUID, *, actor_id: uuid.UUID | None, customer_id: uuid.UUID | None = None
    ) -> Order:
        """POST /orders/{id}/cancel. `customer_id` restricts it to that
        customer's own order (None when staff call it)."""
        order = await self._get_locked(order_id)
        if customer_id is not None and order.customer_id != customer_id:
            raise NotFoundError(f"Order {order_id} not found.")
        if order.status != OrderStatus.PENDING:
            raise ValidationAppError(
                f"Order in status '{order.status}' can no longer be cancelled by the customer."
            )
        return await self.transition_status(
            order_id,
            OrderStatus.CANCELLED,
            actor_id=actor_id,
            source=OrderStatusChangeSource.CUSTOMER_CANCEL,
        )
