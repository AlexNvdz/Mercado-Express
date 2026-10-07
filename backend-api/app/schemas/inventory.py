import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import InventoryChangeKind
from app.schemas.common import ActorOut


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
    reason: str | None = Field(default=None, max_length=255, description="Stored in the inventory history.")


class InventorySetLevel(BaseModel):
    quantity_on_hand: int = Field(..., ge=0)
    reorder_level: int | None = Field(default=None, ge=0)
    reason: str | None = Field(default=None, max_length=255, description="Stored in the inventory history.")


class InventoryChangeOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    kind: InventoryChangeKind
    quantity_on_hand_before: int
    quantity_on_hand_after: int
    quantity_delta: int = Field(..., description="quantity_on_hand_after - quantity_on_hand_before.")
    reorder_level_before: int
    reorder_level_after: int
    reason: str | None
    actor: ActorOut | None = Field(..., description="Who made it; null if that user no longer exists.")
    created_at: datetime

    model_config = {"from_attributes": True}
