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

Envia.com (app/services/envia_client.py), when ENVIA_API_KEY is set: once a
payment commits, a background task buys the cheapest label among
ENVIA_CARRIERS and creates the shipment with it (create_envia_shipment, also
the panel's "Generar guía"); sync_envia_tracking moves the shipment along
what the carrier reports; a cancelled order's unused label is voided.
"""

import abc
import logging
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.exceptions import (
    AppError,
    ConflictError,
    ExternalServiceError,
    InvalidStateTransitionError,
    NotFoundError,
    ValidationAppError,
)
from app.models.enums import OrderStatus, OrderStatusChangeSource, ShipmentStatus
from app.models.order import Order
from app.models.shipment import Shipment
from app.repositories.address_repository import AddressRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.order_status_change_repository import OrderStatusChangeRepository
from app.repositories.shipment_repository import ShipmentRepository
from app.repositories.user_repository import UserRepository
from app.schemas.shipment import ShipmentCreate, ShipmentUpdate
from app.services import envia_client
from app.services.order_service import OrderService

logger = logging.getLogger(__name__)

# Order statuses in which a shipment can be created. Staff may have moved
# the order to `preparing` by hand before creating it.
_SHIPMENT_CREATABLE_ORDER_STATUSES = {OrderStatus.PAID, OrderStatus.PREPARING}
# Shipment statuses before dispatch, in which carrier/tracking can be edited.
_EDITABLE_SHIPMENT_STATUSES = {ShipmentStatus.PENDING, ShipmentStatus.PREPARING}
# Envia tracking statuses that mean the carrier has the package; "delivered"
# closes it. Anything else leaves the shipment alone. Casefolded: generaltrack
# says "Picked Up", the tracking webhook "picked_up"/"delivered".
_ENVIA_IN_TRANSIT = {"picked up", "shipped", "in transit", "out for delivery"}
_ENVIA_DELIVERED = "delivered"
# Orders POST /shipments/envia/retry handles per call: each one is a few
# Envia calls, and the panel waits for the whole batch.
ENVIA_RETRY_BATCH = 10


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
        self.users = UserRepository(db)
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
        await self._check_shipment_creatable(order)
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

    async def _check_shipment_creatable(self, order: Order) -> None:
        if order.status not in _SHIPMENT_CREATABLE_ORDER_STATUSES:
            raise InvalidStateTransitionError(
                f"Order must be 'paid' or 'preparing' to create a shipment (currently '{order.status}')."
            )
        if await self.shipments.get_by_order_id(order.id) is not None:
            raise ConflictError(f"Order {order.id} already has a shipment.")

    async def create_envia_shipment(self, order_id: uuid.UUID, *, actor_id: uuid.UUID | None) -> Shipment:
        """Quotes every ENVIA_CARRIERS service for the order's shipping
        address, buys the cheapest label and creates the shipment with it
        (order -> `preparing`). The order row stays locked during the Envia
        calls, so two runs can't buy two labels for the same order."""
        if not envia_client.enabled():
            raise ValidationAppError("Envia no está configurado (ENVIA_API_KEY).")
        order = await self._get_order_locked(order_id)
        await self._check_shipment_creatable(order)
        address = order.shipping_address
        if address is None:
            raise ValidationAppError("El pedido no tiene dirección de envío.")
        if address.country.upper() != "CO":
            raise ValidationAppError("Envia solo despacha a direcciones en Colombia.")
        customer = await self.users.get(order.customer_id)
        assert customer is not None  # FK
        phone = address.phone or customer.phone
        if not phone:
            raise ValidationAppError("Falta el teléfono de quien recibe el pedido.")

        destination_place = await envia_client.locate(address.state, address.city)
        if destination_place is None:
            raise ValidationAppError(f"Envia no reconoce la ciudad '{address.city}' ({address.state}).")
        origin_place = await envia_client.locate(settings.ENVIA_ORIGIN_STATE, settings.ENVIA_ORIGIN_CITY)
        if origin_place is None:
            raise ExternalServiceError("La dirección de origen ENVIA_ORIGIN_* no es válida para Envia.")
        origin = envia_client.address(
            settings.ENVIA_ORIGIN_NAME,
            settings.ENVIA_ORIGIN_PHONE,
            settings.ENVIA_ORIGIN_STREET,
            origin_place,
        )
        destination = envia_client.address(
            customer.full_name, phone, address.line1, destination_place, customer.email, address.line2
        )
        parcel = envia_client.package(Decimal(order.subtotal))

        rates = await envia_client.rates(origin, destination, parcel)
        label = await envia_client.generate(
            origin, destination, parcel, min(rates, key=lambda r: r.total_price)
        )
        shipment = await self.shipments.create(
            {
                "order_id": order.id,
                "address_id": address.id,
                "carrier": label.carrier,
                "service": label.service,
                "tracking_number": label.tracking_number,
                "tracking_url": label.tracking_url,
                "label_url": label.label_url,
                "shipping_cost": label.total_price,
                "status": ShipmentStatus.PREPARING,
            }
        )
        await self._move_order(
            order, OrderStatus.PREPARING, OrderStatusChangeSource.SHIPMENT_CREATED, actor_id
        )
        await self.db.flush()
        return shipment

    async def sync_envia_tracking(
        self, shipment_id: uuid.UUID, *, actor_id: uuid.UUID | None
    ) -> tuple[Shipment, str]:
        """Asks Envia where the package is and moves the shipment to match:
        picked up/in transit -> mark_shipped, delivered -> mark_delivered
        (both, in order, if it was delivered before anyone synced). Returns
        the shipment and Envia's status name."""
        shipment = await self._get(shipment_id)
        if not shipment.label_url or not shipment.tracking_number:
            raise ValidationAppError("Este envío no tiene guía de Envia.")
        if not envia_client.enabled():
            raise ValidationAppError("Envia no está configurado (ENVIA_API_KEY).")
        carrier_status = await envia_client.track(shipment.tracking_number)
        return await self.apply_carrier_status(shipment, carrier_status, actor_id=actor_id), carrier_status

    async def apply_carrier_status(
        self, shipment: Shipment, carrier_status: str, *, actor_id: uuid.UUID | None
    ) -> Shipment:
        """Moves the shipment to match what the carrier reports (sync and the
        Envia webhook): picked up/in transit -> mark_shipped, delivered ->
        mark_delivered (both, in order, if nobody saw the pickup). A status
        the shipment already passed changes nothing, so repeats are no-ops."""
        status = carrier_status.replace("_", " ").casefold().strip()
        moved = status in _ENVIA_IN_TRANSIT or status == _ENVIA_DELIVERED
        if moved and shipment.status == ShipmentStatus.PREPARING:
            shipment = await self.mark_shipped(shipment.id, actor_id=actor_id)
        if status == _ENVIA_DELIVERED and shipment.status == ShipmentStatus.IN_TRANSIT:
            shipment = await self.mark_delivered(shipment.id, actor_id=actor_id)
        return shipment

    async def handle_envia_webhook(self, payload: Any) -> Shipment | None:
        """Envia's tracking webhook. Real deliveries (checked 2026-11-11) are
        `{"type": "tracking.simple", "data": {"tracking_number", "status":
        "Created", ...}}`; its test call (POST /ship/webhooktest/) sends a flat
        `{"carrier", "tracking_number", "shipment_status": "Picked Up"}`.
        Returns None when it's not about one of our labels; Envia gets a 200
        either way so it doesn't retry."""
        data = payload.get("data", payload) if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            return None
        tracking_number = data.get("tracking_number")
        status = data.get("status") or data.get("shipment_status")
        if not isinstance(tracking_number, str) or not isinstance(status, str):
            return None
        shipment = await self.shipments.get_by_tracking_number(tracking_number)
        if shipment is None or not shipment.label_url:
            return None
        return await self.apply_carrier_status(shipment, status, actor_id=None)

    async def retry_envia_shipments(self) -> tuple[int, list[tuple[uuid.UUID, str, str]], int]:
        """Buys the label for up to ENVIA_RETRY_BATCH `paid` Colombian orders
        (a paid order has no shipment: creating one moves it to `preparing`),
        each in its own savepoint so one failure doesn't undo the others.
        Returns (labels created, (order id, order number, reason) per
        failure, paid CO orders still left)."""
        if not envia_client.enabled():
            raise ValidationAppError("Envia no está configurado (ENVIA_API_KEY).")
        orders, total = await OrderService(self.db).list_orders(
            customer_id=None, statuses=[OrderStatus.PAID], country="CO", offset=0, limit=ENVIA_RETRY_BATCH
        )
        # Plain values: a rolled-back savepoint expires the order objects.
        pending = [(o.id, o.order_number) for o in orders]
        created, failed = 0, []
        for order_id, order_number in pending:
            try:
                async with self.db.begin_nested():
                    await self.create_envia_shipment(order_id, actor_id=None)
                created += 1
            except AppError as exc:
                failed.append((order_id, order_number, exc.detail))
        return created, failed, total - created

    async def update_shipment(self, shipment_id: uuid.UUID, data: ShipmentUpdate) -> Shipment:
        """Edit carrier/tracking number; only before dispatch, and never on an
        Envia label (it would stop matching what Envia has)."""
        shipment = await self._get(shipment_id)
        if shipment.label_url:
            raise ConflictError("El envío tiene guía de Envia: la transportadora y la guía no se editan.")
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


async def schedule_envia_label(
    db: AsyncSession, background_tasks: BackgroundTasks, order_id: uuid.UUID
) -> None:
    """After a completed payment: commit now and buy the label once the
    response is out (FastAPI commits get_db only after background tasks have
    run, so the task's own session would not see the order otherwise)."""
    if not envia_client.enabled():
        return
    await db.commit()
    background_tasks.add_task(auto_create_envia_shipment, order_id)


async def auto_create_envia_shipment(order_id: uuid.UUID) -> None:
    """Background task, own session. A failure only logs: the order stays
    `paid` and staff retry from the panel (POST /shipments/order/{id}/envia)."""
    async with AsyncSessionLocal() as db:
        try:
            await ShipmentService(db).create_envia_shipment(order_id, actor_id=None)
            await db.commit()
        except AppError as exc:
            await db.rollback()
            logger.warning("Automatic Envia label for order %s failed: %s", order_id, exc.detail)
        except Exception:
            await db.rollback()
            logger.exception("Automatic Envia label for order %s failed", order_id)


async def schedule_envia_cancel(
    db: AsyncSession, background_tasks: BackgroundTasks, order_id: uuid.UUID
) -> None:
    """After an order was cancelled/refunded: void its undispatched Envia
    label once the cancellation is committed."""
    shipment = await ShipmentRepository(db).get_by_order_id(order_id)
    if (
        shipment is None
        or shipment.status != ShipmentStatus.CANCELLED
        or not shipment.label_url
        or not shipment.carrier
        or not shipment.tracking_number
        or not envia_client.enabled()
    ):
        return
    await db.commit()
    background_tasks.add_task(envia_client.cancel_quietly, shipment.carrier, shipment.tracking_number)
