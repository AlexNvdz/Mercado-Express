import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class InventoryOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    quantity_on_hand: int
    quantity_reserved: int
    quantity_available: int
    reorder_level: int
    updated_at: datetime

    model_config = {"from_attributes": True}


class InventoryAdjust(BaseModel):
    """Adjust on-hand stock by a signed delta (e.g. +50 restock, -3 shrinkage)."""

    delta: int = Field(..., description="Positive to add stock, negative to remove.")
    reason: str | None = Field(default=None, max_length=255)


class InventorySetLevel(BaseModel):
    quantity_on_hand: int = Field(..., ge=0)
    reorder_level: int | None = Field(default=None, ge=0)
