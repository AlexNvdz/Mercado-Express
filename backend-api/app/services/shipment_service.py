"""Shipment (despacho) orchestration. Carrier integration is abstracted the
same way as payments -- see `ShipmentCarrier` -- so a real logistics
provider can be added later without a schema or router change.

Lifecycle: created `preparing` (order `paid` or already `preparing`), then
`in_transit` (dispatched: the order's stock reservation becomes a real
stock decrement, exactly once) and `delivered`. Carrier and tracking number
can be set at creation and edited until dispatch. An undispatched shipment
becomes `cancelled` if its order is cancelled/refunded (OrderService).

Every method that changes an order's status locks the order row first (see
OrderRepository.get_with_items), so concurrent requests on the same order
are serialized.
"""

import abc
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ConflictError, InvalidStateTransitionError, NotFoundError
from app.models.enums import OrderStatus, OrderStatusChangeSource, ShipmentStatus
from app.models.order import Order
from app.models.shipment import Shipment
from app.repositories.address_repository import AddressRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.order_status_change_repository import OrderStatusChangeRepository
from app.repositories.shipment_repository import ShipmentRepository
from app.schemas.shipment import ShipmentCreate, ShipmentUpdate

# Order statuses in which a shipment can be created. Staff may have moved
# the order to `preparing` by hand before creating it.
_SHIPMENT_CREATABLE_ORDER_STATUSES = {OrderStatus.PAID, OrderStatus.PREPARING}
# Shipment statuses before dispatch, in which carrier/tracking can be edited.
_EDITABLE_SHIPMENT_STATUSES = {ShipmentStatus.PENDING, ShipmentStatus.PREPARING}


class ShipmentCarrier(abc.ABC):
    @abc.abstractmethod
    async def generate_tracking_number(self, shipment: Shipment) -> str: ...


class ManualShipmentCarrier(ShipmentCarrier):
    """No real carrier configured yet: generates a placeholder tracking
    number. Swap for a real integration later without touching callers."""

    async def generate_tracking_number(self, shipment: Shipment) -> str:
        return f"MANUAL-{shipment.id.hex[:10].upper()}"


class ShipmentService:
    def __init__(self, db: AsyncSession, carrier: ShipmentCarrier | None = None) -> None:
        self.db = db
        self.shipments = ShipmentRepository(db)
        self.orders = OrderRepository(db)
        self.addresses = AddressRepository(db)
        self.inventory = InventoryRepository(db)
        self.status_changes = OrderStatusChangeRepository(db)
        self.carrier = carrier or ManualShipmentCarrier()

    async def _move_order(
        self,
        order: Order,
        to_status: OrderStatus,
        source: OrderStatusChangeSource,
        actor_id: uuid.UUID | None,
    ) -> None:
        """Sets the order's status and records it in its history; no-op
        (and no history entry) if the order is already there."""
        if order.status == to_status:
            return
        await self.status_changes.record(
            order_id=order.id, from_status=order.status, to_status=to_status, source=source, actor_id=actor_id
        )
        order.status = to_status

    async def create_shipment(
        self, order_id: uuid.UUID, data: ShipmentCreate, *, actor_id: uuid.UUID | None
    ) -> Shipment:
        order = await self._get_order_locked(order_id)
        if order.status not in _SHIPMENT_CREATABLE_ORDER_STATUSES:
            raise InvalidStateTransitionError(
                f"Order must be 'paid' or 'preparing' to create a shipment (currently '{order.status}')."
            )
        if await self.shipments.get_by_order_id(order.id) is not None:
            raise ConflictError(f"Order {order_id} already has a shipment.")
        address = await self.addresses.get(data.address_id)
        if address is None:
            raise NotFoundError(f"Address {data.address_id} not found.")

        shipment = await self.shipments.create(
            {
                "order_id": order.id,
                "address_id": data.address_id,
                "carrier": data.carrier,
                "tracking_number": data.tracking_number,
                "status": ShipmentStatus.PREPARING,
            }
        )
        # No-op if staff already moved the order to `preparing` by hand.
        await self._move_order(
            order, OrderStatus.PREPARING, OrderStatusChangeSource.SHIPMENT_CREATED, actor_id
        )
        await self.db.flush()
        return shipment

    async def update_shipment(self, shipment_id: uuid.UUID, data: ShipmentUpdate) -> Shipment:
        """Edit carrier/tracking number; only before dispatch."""
        shipment = await self._get(shipment_id)
        if shipment.status not in _EDITABLE_SHIPMENT_STATUSES:
            raise InvalidStateTransitionError(
                f"Shipment can only be edited before dispatch (currently '{shipment.status}')."
            )
        return await self.shipments.update(shipment, data.model_dump(exclude_unset=True))

    async def mark_shipped(self, shipment_id: uuid.UUID, *, actor_id: uuid.UUID | None) -> Shipment:
        shipment = await self._get(shipment_id)
        order = await self._get_order_locked(shipment.order_id)
        # Re-read under the order lock: a concurrent request may have just
        # dispatched or cancelled this shipment.
        await self.db.refresh(shipment)
        if shipment.status != ShipmentStatus.PREPARING:
            raise InvalidStateTransitionError(
                f"Shipment must be 'preparing' to ship (currently '{shipment.status}')."
            )
        if order.status != OrderStatus.PREPARING:
            raise InvalidStateTransitionError(
                f"Order must be 'preparing' to ship (currently '{order.status}')."
            )

        # The only place stock is fulfilled: the checks above let each
        # shipment (and so each order) through here once.
        for item in order.items:
            await self.inventory.fulfill(item.product_id, item.quantity)

        shipment.status = ShipmentStatus.IN_TRANSIT
        if not shipment.tracking_number:
            shipment.tracking_number = await self.carrier.generate_tracking_number(shipment)
        shipment.shipped_at = datetime.now(UTC)
        await self._move_order(
            order, OrderStatus.SHIPPED, OrderStatusChangeSource.SHIPMENT_DISPATCHED, actor_id
        )
        await self.db.flush()
        # See order_service.transition_status for why this refresh matters:
        # `updated_at` is server-computed (onupdate=func.now()) and is
        # returned straight to a response model with no further query.
        await self.db.refresh(shipment)
        return shipment

    async def mark_delivered(self, shipment_id: uuid.UUID, *, actor_id: uuid.UUID | None) -> Shipment:
        shipment = await self._get(shipment_id)
        order = await self._get_order_locked(shipment.order_id)
        await self.db.refresh(shipment)
        if shipment.status != ShipmentStatus.IN_TRANSIT:
            raise InvalidStateTransitionError(
                f"Shipment must be 'in_transit' to deliver (currently '{shipment.status}')."
            )

        shipment.status = ShipmentStatus.DELIVERED
        shipment.delivered_at = datetime.now(UTC)
        await self._move_order(
            order, OrderStatus.DELIVERED, OrderStatusChangeSource.SHIPMENT_DELIVERED, actor_id
        )
        await self.db.flush()
        await self.db.refresh(shipment)
        return shipment

    async def _get(self, shipment_id: uuid.UUID) -> Shipment:
        shipment = await self.shipments.get(shipment_id)
        if shipment is None:
            raise NotFoundError(f"Shipment {shipment_id} not found.")
        return shipment

    async def _get_order_locked(self, order_id: uuid.UUID) -> Order:
        order = await self.orders.get_with_items(order_id, for_update=True)
        if order is None:
            raise NotFoundError(f"Order {order_id} not found.")
        return order

    async def get_for_order(self, order_id: uuid.UUID) -> Shipment:
        shipment = await self.shipments.get_by_order_id(order_id)
        if shipment is None:
            raise NotFoundError(f"No shipment for order {order_id}.")
        return shipment
