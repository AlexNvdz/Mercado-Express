import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import PaginationParams, get_current_user, pagination_params, require_staff
from app.models.enums import OrderStatus, UserRole
from app.models.user import User
from app.schemas.common import Page
from app.schemas.order import OrderCreate, OrderOut, OrderStatusChangeOut, OrderStatusUpdate
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
    statuses: list[OrderStatus] | None = Query(
        default=None,
        alias="status",
        description="Only orders in these statuses; repeat it for several: ?status=paid&status=preparing.",
    ),
    pagination: PaginationParams = Depends(pagination_params),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Page[OrderOut]:
    """Customers see only their own orders; staff/admin see every order.
    `total`/`pages` count the same filters."""
    customer_id = current_user.id if current_user.role == UserRole.CUSTOMER else None
    items, total = await OrderService(db).list_orders(
        customer_id=customer_id, statuses=statuses, offset=pagination.offset, limit=pagination.page_size
    )
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


@router.get(
    "/{order_id}/history", response_model=list[OrderStatusChangeOut], dependencies=[Depends(require_staff)]
)
async def get_order_history(
    order_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> list[OrderStatusChangeOut]:
    """Staff/admin only: every status change of the order, oldest first --
    who made it, from/to status and what triggered it."""
    changes = await OrderService(db).history(order_id)
    return [OrderStatusChangeOut.model_validate(c) for c in changes]


@router.post("/{order_id}/cancel", response_model=OrderOut)
async def cancel_order(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderOut:
    service = OrderService(db)
    customer_id = current_user.id if current_user.role == UserRole.CUSTOMER else None
    order = await service.cancel(order_id, actor_id=current_user.id, customer_id=customer_id)
    return OrderOut.model_validate(order)


@router.patch("/{order_id}/status", response_model=OrderOut)
async def update_order_status(
    order_id: uuid.UUID,
    data: OrderStatusUpdate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> OrderOut:
    """Staff/admin only: manual corrections (paid -> preparing, cancel,
    refund), checked against OrderService's _ALLOWED_TRANSITIONS. Payment,
    dispatch and delivery go through /payments and /shipments instead."""
    order = await OrderService(db).transition_status(order_id, data.status, actor_id=current_user.id)
    return OrderOut.model_validate(order)
