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
    revenue: Decimal = Field(
        ..., description="Sum of line_total across items of paid orders that were not reversed."
    )


class ReportSummary(BaseModel):
    net_revenue: Decimal = Field(
        ...,
        description="gross_revenue - refunded_amount: the sum of the whole Sale ledger, "
        "not Order.total_amount.",
    )
    gross_revenue: Decimal = Field(..., description="Sum of `sale` entries: every order ever paid.")
    refunded_amount: Decimal = Field(
        ...,
        description="Sum of `reversal` entries as a positive amount: paid orders later "
        "cancelled or refunded.",
    )
    sale_count: int = Field(..., description="Number of `sale` entries (orders ever paid).")
    reversal_count: int = Field(..., description="Number of `reversal` entries.")
    orders_by_status: list[OrderStatusCount]
    top_products: list[TopProduct]
    customer_count: int
    product_count: int
    generated_at: datetime
