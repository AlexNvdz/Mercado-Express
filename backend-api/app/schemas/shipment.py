import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field

from app.models.enums import ShipmentStatus


def _blank_to_none(value: object) -> object:
    """Trims text; an empty or whitespace-only value means "not set"."""
    if isinstance(value, str):
        return value.strip() or None
    return value


# max_length sits on the `str` member: blank input reaches the union as None.
_OptionalText = Annotated[Annotated[str, Field(max_length=100)] | None, BeforeValidator(_blank_to_none)]


class ShipmentCreate(BaseModel):
    address_id: uuid.UUID
    carrier: _OptionalText = None
    tracking_number: _OptionalText = None


class ShipmentUpdate(BaseModel):
    """Partial update, allowed only before dispatch: only the fields sent
    are changed, and null (or blank) clears one."""

    carrier: _OptionalText = None
    tracking_number: _OptionalText = None


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
