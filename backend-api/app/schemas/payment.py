import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import PaymentStatus


class PaymentCreate(BaseModel):
    order_id: uuid.UUID
    method: str | None = Field(default=None, max_length=50, description="card, cash, transfer, ...")
    provider: str | None = Field(
        default=None, max_length=50, description="Payment provider; 'manual' when none is integrated yet."
    )


class PaymentOut(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    amount: Decimal
    currency: str
    status: PaymentStatus
    provider: str | None
    provider_reference: str | None
    method: str | None
    paid_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
