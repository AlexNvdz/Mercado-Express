import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import OrderStatus


class OrderStatusCount(BaseModel):
    status: OrderStatus
    count: int


class TopProduct(BaseModel):
    product_id: uuid.UUID
    name: str
    sku: str
    units_sold: int
    revenue: Decimal = Field(..., description="Sum of line_total across sold order items.")


class ReportSummary(BaseModel):
    total_revenue: Decimal = Field(
        ..., description="Sum of Sale.total_amount -- the immutable ledger, not Order.total_amount."
    )
    sale_count: int
    orders_by_status: list[OrderStatusCount]
    top_products: list[TopProduct]
    customer_count: int
    product_count: int
    generated_at: datetime
