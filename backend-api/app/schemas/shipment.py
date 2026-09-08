import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import ShipmentStatus


class ShipmentCreate(BaseModel):
    address_id: uuid.UUID
    carrier: str | None = Field(default=None, max_length=100)


class ShipmentStatusUpdate(BaseModel):
    status: ShipmentStatus
    tracking_number: str | None = Field(default=None, max_length=100)


class ShipmentOut(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    address_id: uuid.UUID
    status: ShipmentStatus
    carrier: str | None
    tracking_number: str | None
    shipped_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
