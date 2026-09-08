"""Shipment (despacho) orchestration. Carrier integration is abstracted the
same way as payments -- see `ShipmentCarrier` -- so a real logistics
provider can be added later without a schema or router change."""

import abc
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import InvalidStateTransitionError, NotFoundError
from app.models.enums import OrderStatus, ShipmentStatus
from app.models.shipment import Shipment
from app.repositories.address_repository import AddressRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.shipment_repository import ShipmentRepository
from app.schemas.shipment import ShipmentCreate


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
        self.carrier = carrier or ManualShipmentCarrier()

    async def create_shipment(self, order_id: uuid.UUID, data: ShipmentCreate) -> Shipment:
        order = await self.orders.get_with_items(order_id)
        if order is None:
            raise NotFoundError(f"Order {order_id} not found.")
        if order.status != OrderStatus.PAID:
            raise InvalidStateTransitionError(
                f"Order must be 'paid' before preparing a shipment (currently '{order.status}')."
            )
        address = await self.addresses.get(data.address_id)
        if address is None:
            raise NotFoundError(f"Address {data.address_id} not found.")

        shipment = await self.shipments.create(
            {
                "order_id": order.id,
                "address_id": data.address_id,
                "carrier": data.carrier,
                "status": ShipmentStatus.PREPARING,
            }
        )
        order.status = OrderStatus.PREPARING
        await self.db.flush()
        return shipment

    async def mark_shipped(self, shipment_id: uuid.UUID) -> Shipment:
        shipment = await self._get(shipment_id)
        if shipment.status != ShipmentStatus.PREPARING:
            raise InvalidStateTransitionError(
                f"Shipment must be 'preparing' to ship (currently '{shipment.status}')."
            )
        order = await self.orders.get_with_items(shipment.order_id)
        assert order is not None
        for item in order.items:
            await self.inventory.fulfill(item.product_id, item.quantity)

        shipment.status = ShipmentStatus.IN_TRANSIT
        shipment.tracking_number = await self.carrier.generate_tracking_number(shipment)
        shipment.shipped_at = datetime.now(UTC)
        order.status = OrderStatus.SHIPPED
        await self.db.flush()
        # See order_service.transition_status for why this refresh matters:
        # `updated_at` is server-computed (onupdate=func.now()) and is
        # returned straight to a response model with no further query.
        await self.db.refresh(shipment)
        return shipment

    async def mark_delivered(self, shipment_id: uuid.UUID) -> Shipment:
        shipment = await self._get(shipment_id)
        if shipment.status != ShipmentStatus.IN_TRANSIT:
            raise InvalidStateTransitionError(
                f"Shipment must be 'in_transit' to deliver (currently '{shipment.status}')."
            )
        order = await self.orders.get(shipment.order_id)
        assert order is not None

        shipment.status = ShipmentStatus.DELIVERED
        shipment.delivered_at = datetime.now(UTC)
        order.status = OrderStatus.DELIVERED
        await self.db.flush()
        await self.db.refresh(shipment)
        return shipment

    async def _get(self, shipment_id: uuid.UUID) -> Shipment:
        shipment = await self.shipments.get(shipment_id)
        if shipment is None:
            raise NotFoundError(f"Shipment {shipment_id} not found.")
        return shipment

    async def get_for_order(self, order_id: uuid.UUID) -> Shipment:
        shipment = await self.shipments.get_by_order_id(order_id)
        if shipment is None:
            raise NotFoundError(f"No shipment for order {order_id}.")
        return shipment
