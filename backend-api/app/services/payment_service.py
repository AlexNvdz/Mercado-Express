"""Payment processing, abstracted behind `PaymentGateway` so a real provider
(Stripe, MercadoPago, ...) can be plugged in later without touching the
service or router. No real gateway is wired up yet -- `ManualPaymentGateway`
just marks the payment completed immediately, which is enough to exercise
the order -> paid -> preparing -> shipped -> delivered flow end to end."""

import abc
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import InvalidStateTransitionError, NotFoundError
from app.models.enums import OrderStatus, PaymentStatus
from app.models.payment import Payment
from app.models.sale import Sale
from app.repositories.order_repository import OrderRepository
from app.repositories.payment_repository import PaymentRepository
from app.schemas.payment import PaymentCreate


class PaymentGateway(abc.ABC):
    """Port for an external payment provider."""

    @abc.abstractmethod
    async def charge(self, payment: Payment) -> tuple[PaymentStatus, str | None]:
        """Attempt to charge `payment`. Returns (resulting_status, provider_reference)."""


class ManualPaymentGateway(PaymentGateway):
    """No real provider configured yet: marks every payment completed
    immediately. Swap for a real gateway (e.g. Stripe) once credentials and
    a provider are chosen -- the rest of the system is unaffected."""

    async def charge(self, payment: Payment) -> tuple[PaymentStatus, str | None]:
        return PaymentStatus.COMPLETED, f"manual-{payment.id}"


class PaymentService:
    def __init__(self, db: AsyncSession, gateway: PaymentGateway | None = None) -> None:
        self.db = db
        self.payments = PaymentRepository(db)
        self.orders = OrderRepository(db)
        self.gateway = gateway or ManualPaymentGateway()

    async def create_payment(self, data: PaymentCreate) -> Payment:
        order = await self.orders.get(data.order_id)
        if order is None:
            raise NotFoundError(f"Order {data.order_id} not found.")
        if order.status not in (OrderStatus.PENDING, OrderStatus.AWAITING_PAYMENT):
            raise InvalidStateTransitionError(
                f"Order in status '{order.status}' cannot accept a new payment."
            )

        payment = await self.payments.create(
            {
                "order_id": order.id,
                "amount": order.total_amount,
                "status": PaymentStatus.PENDING,
                "provider": data.provider or "manual",
                "method": data.method,
            }
        )

        status, reference = await self.gateway.charge(payment)
        payment.status = status
        payment.provider_reference = reference
        if status == PaymentStatus.COMPLETED:
            payment.paid_at = datetime.now(UTC)
            order.status = OrderStatus.PAID
            self.db.add(
                Sale(order_id=order.id, total_amount=order.total_amount)
            )
        elif status == PaymentStatus.FAILED:
            order.status = OrderStatus.AWAITING_PAYMENT

        await self.db.flush()
        await self.db.refresh(payment)
        return payment

    async def get(self, payment_id: uuid.UUID) -> Payment:
        payment = await self.payments.get(payment_id)
        if payment is None:
            raise NotFoundError(f"Payment {payment_id} not found.")
        return payment

    async def list_for_order(self, order_id: uuid.UUID) -> list[Payment]:
        return await self.payments.list_for_order(order_id)
