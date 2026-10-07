"""Shared response envelopes: pagination, error payloads, history actors."""

import uuid
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from app.models.enums import UserRole

T = TypeVar("T")


class ActorOut(BaseModel):
    """The user who made a recorded change (order/inventory history)."""

    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole

    model_config = {"from_attributes": True}


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int = Field(..., description="Total number of matching records.")
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1)
    pages: int = Field(..., ge=0)


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = Field(default=None, description="Machine-readable error code.")
