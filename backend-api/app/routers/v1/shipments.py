import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user, require_staff
from app.exceptions import NotFoundError
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.shipment import ShipmentCreate, ShipmentOut, ShipmentSyncOut, ShipmentUpdate
from app.services.order_service import OrderService
from app.services.shipment_service import ShipmentService

router = APIRouter(prefix="/shipments", tags=["shipments"])


@router.post("/order/{order_id}", response_model=ShipmentOut, status_code=status.HTTP_201_CREATED)
async def create_shipment(
    order_id: uuid.UUID,
    data: ShipmentCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> ShipmentOut:
    """Staff/admin only: begin preparing a shipment for a `paid` or
    `preparing` order, optionally with carrier and tracking number."""
    shipment = await ShipmentService(db).create_shipment(order_id, data, actor_id=current_user.id)
    return ShipmentOut.model_validate(shipment)


@router.post("/order/{order_id}/envia", response_model=ShipmentOut, status_code=status.HTTP_201_CREATED)
async def create_envia_shipment(
    order_id: uuid.UUID,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> ShipmentOut:
    """Staff/admin only: buy the cheapest Envia label for the order's
    shipping address and create the shipment with it -- what already runs
    on its own after a payment, for when that failed. 502 if Envia fails."""
    shipment = await ShipmentService(db).create_envia_shipment(order_id, actor_id=current_user.id)
    return ShipmentOut.model_validate(shipment)


@router.post("/{shipment_id}/sync", response_model=ShipmentSyncOut)
async def sync_shipment(
    shipment_id: uuid.UUID,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> ShipmentSyncOut:
    """Staff/admin only: read the Envia label's tracking and dispatch or
    deliver the shipment if the carrier says so."""
    shipment, carrier_status = await ShipmentService(db).sync_envia_tracking(
        shipment_id, actor_id=current_user.id
    )
    return ShipmentSyncOut.model_validate(
        {**ShipmentOut.model_validate(shipment).model_dump(), "carrier_status": carrier_status}
    )


@router.patch("/{shipment_id}", response_model=ShipmentOut, dependencies=[Depends(require_staff)])
async def update_shipment(
    shipment_id: uuid.UUID, data: ShipmentUpdate, db: AsyncSession = Depends(get_db)
) -> ShipmentOut:
    """Staff/admin only: edit carrier/tracking number before dispatch
    (409 on an Envia label)."""
    shipment = await ShipmentService(db).update_shipment(shipment_id, data)
    return ShipmentOut.model_validate(shipment)


@router.post("/{shipment_id}/ship", response_model=ShipmentOut)
async def ship_shipment(
    shipment_id: uuid.UUID,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> ShipmentOut:
    """Staff/admin only: mark the shipment dispatched (decrements real stock;
    keeps the tracking number staff entered, or generates one)."""
    shipment = await ShipmentService(db).mark_shipped(shipment_id, actor_id=current_user.id)
    return ShipmentOut.model_validate(shipment)


@router.post("/{shipment_id}/deliver", response_model=ShipmentOut)
async def deliver_shipment(
    shipment_id: uuid.UUID,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> ShipmentOut:
    """Staff/admin only: mark the shipment delivered, closing the order."""
    shipment = await ShipmentService(db).mark_delivered(shipment_id, actor_id=current_user.id)
    return ShipmentOut.model_validate(shipment)


@router.get("/order/{order_id}", response_model=ShipmentOut)
async def get_shipment_for_order(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ShipmentOut:
    if current_user.role == UserRole.CUSTOMER:
        order = await OrderService(db).get(order_id)
        if order.customer_id != current_user.id:
            raise NotFoundError(f"Order {order_id} not found.")
    shipment = ShipmentOut.model_validate(await ShipmentService(db).get_for_order(order_id))
    if current_user.role == UserRole.CUSTOMER:
        # What the store paid and the printable label are staff business.
        return shipment.model_copy(update={"label_url": None, "shipping_cost": None})
    return shipment
