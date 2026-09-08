"""Shared response envelopes: pagination and error payloads."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int = Field(..., description="Total number of matching records.")
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1)
    pages: int = Field(..., ge=0)


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = Field(default=None, description="Machine-readable error code.")
