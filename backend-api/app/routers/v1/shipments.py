import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user, require_staff
from app.exceptions import NotFoundError
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.shipment import ShipmentCreate, ShipmentOut, ShipmentUpdate
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


@router.patch("/{shipment_id}", response_model=ShipmentOut, dependencies=[Depends(require_staff)])
async def update_shipment(
    shipment_id: uuid.UUID, data: ShipmentUpdate, db: AsyncSession = Depends(get_db)
) -> ShipmentOut:
    """Staff/admin only: edit carrier/tracking number before dispatch."""
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
    shipment = await ShipmentService(db).get_for_order(order_id)
    return ShipmentOut.model_validate(shipment)
