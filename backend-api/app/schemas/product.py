import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

# Lowest price (COP) a product may be created, edited or sold at. Only input
# schemas enforce it: older rows (Olist BRL prices, legacy demo data) still
# have to serialize in ProductOut, and OrderService refuses to sell them.
MIN_PRODUCT_PRICE = Decimal("5900.00")


class ProductBase(BaseModel):
    sku: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    category_id: uuid.UUID
    price: Decimal = Field(..., ge=0, decimal_places=2)
    is_active: bool = True


class ProductCreate(ProductBase):
    price: Decimal = Field(..., ge=MIN_PRODUCT_PRICE, decimal_places=2)


class ProductUpdate(BaseModel):
    sku: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    category_id: uuid.UUID | None = None
    price: Decimal | None = Field(default=None, ge=MIN_PRODUCT_PRICE, decimal_places=2)
    is_active: bool | None = None


class ProductImageOut(BaseModel):
    id: uuid.UUID
    url: str
    position: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductOut(ProductBase):
    id: uuid.UUID
    images: list[ProductImageOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
