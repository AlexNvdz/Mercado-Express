import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.exceptions import NotFoundError
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.payment import PaymentCreate, PaymentOut
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
async def create_payment(
    data: PaymentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaymentOut:
    """Pay for an order. No real payment gateway is integrated yet -- see
    app/services/payment_service.py::ManualPaymentGateway. A customer may
    only pay their own order."""
    if current_user.role == UserRole.CUSTOMER:
        order = await OrderService(db).get(data.order_id)
        if order.customer_id != current_user.id:
            raise NotFoundError(f"Order {data.order_id} not found.")
    payment = await PaymentService(db).create_payment(data)
    return PaymentOut.model_validate(payment)


@router.get("/{payment_id}", response_model=PaymentOut)
async def get_payment(
    payment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaymentOut:
    payment = await PaymentService(db).get(payment_id)
    if current_user.role == UserRole.CUSTOMER:
        order = await OrderService(db).get(payment.order_id)
        if order.customer_id != current_user.id:
            raise NotFoundError(f"Payment {payment_id} not found.")
    return PaymentOut.model_validate(payment)


@router.get("/order/{order_id}", response_model=list[PaymentOut])
async def list_payments_for_order(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PaymentOut]:
    if current_user.role == UserRole.CUSTOMER:
        order = await OrderService(db).get(order_id)
        if order.customer_id != current_user.id:
            raise NotFoundError(f"Order {order_id} not found.")
    payments = await PaymentService(db).list_for_order(order_id)
    return [PaymentOut.model_validate(p) for p in payments]
