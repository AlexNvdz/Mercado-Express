import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import OrderStatus, OrderStatusChangeSource
from app.schemas.address import AddressOut
from app.schemas.common import ActorOut


class OrderItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(..., gt=0)


class OrderCreate(BaseModel):
    items: list[OrderItemCreate] = Field(..., min_length=1)
    shipping_address_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=2000)


class OrderItemOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    unit_price: Decimal
    line_total: Decimal

    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: uuid.UUID
    order_number: str
    customer_id: uuid.UUID
    status: OrderStatus
    subtotal: Decimal
    tax_amount: Decimal
    shipping_amount: Decimal
    total_amount: Decimal
    shipping_address_id: uuid.UUID | None
    shipping_address: AddressOut | None = None
    notes: str | None
    items: list[OrderItemOut]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderStatusChangeOut(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    from_status: OrderStatus | None = Field(..., description="null only for the `order_created` entry.")
    to_status: OrderStatus
    source: OrderStatusChangeSource
    actor: ActorOut | None = Field(..., description="Who triggered it; null if that user no longer exists.")
    created_at: datetime

    model_config = {"from_attributes": True}
