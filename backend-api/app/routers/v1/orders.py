import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import PaginationParams, get_current_user, pagination_params, require_staff
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.common import Page
from app.schemas.order import OrderCreate, OrderOut, OrderStatusUpdate
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def create_order(
    data: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderOut:
    """Create an order for the current (customer) user. Validates products,
    reserves inventory and computes totals -- see OrderService.create_order."""
    order = await OrderService(db).create_order(current_user.id, data)
    return OrderOut.model_validate(order)


@router.get("", response_model=Page[OrderOut])
async def list_orders(
    pagination: PaginationParams = Depends(pagination_params),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Page[OrderOut]:
    """Customers see only their own orders; staff/admin see every order."""
    service = OrderService(db)
    if current_user.role == UserRole.CUSTOMER:
        items, total = await service.list_for_customer(
            current_user.id, offset=pagination.offset, limit=pagination.page_size
        )
    else:
        items, total = await service.list_all(offset=pagination.offset, limit=pagination.page_size)
    pages = (total + pagination.page_size - 1) // pagination.page_size if total else 0
    return Page(
        items=[OrderOut.model_validate(i) for i in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=pages,
    )


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderOut:
    service = OrderService(db)
    if current_user.role == UserRole.CUSTOMER:
        order = await service.get_for_customer(order_id, current_user.id)
    else:
        order = await service.get(order_id)
    return OrderOut.model_validate(order)


@router.post("/{order_id}/cancel", response_model=OrderOut)
async def cancel_order(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderOut:
    service = OrderService(db)
    customer_id = current_user.id if current_user.role == UserRole.CUSTOMER else None
    order = await service.cancel(order_id, customer_id=customer_id)
    return OrderOut.model_validate(order)


@router.patch("/{order_id}/status", response_model=OrderOut, dependencies=[Depends(require_staff)])
async def update_order_status(
    order_id: uuid.UUID, data: OrderStatusUpdate, db: AsyncSession = Depends(get_db)
) -> OrderOut:
    """Staff/admin only: advance order status directly (e.g. mark paid manually).
    Prefer the /payments and /shipments endpoints for the normal flow."""
    order = await OrderService(db).transition_status(order_id, data.status)
    return OrderOut.model_validate(order)
