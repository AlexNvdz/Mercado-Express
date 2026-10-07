"""Read-only aggregate queries backing GET /reports/summary.

Revenue and per-product units sold are computed from the immutable `sales`
ledger (joined to `order_items`), never from `Order.total_amount` -- an
order's total can be superseded by cancellation/refund, but a `Sale` row is
only ever created once, at the moment a payment completes.
"""

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import OrderStatus, UserRole
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.sale import Sale
from app.models.user import User


class ReportRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def total_revenue(self) -> Decimal:
        result = await self.db.execute(select(func.coalesce(func.sum(Sale.total_amount), 0)))
        return Decimal(result.scalar_one())

    async def sale_count(self) -> int:
        result = await self.db.execute(select(func.count()).select_from(Sale))
        return int(result.scalar_one())

    async def order_counts_by_status(self) -> dict[OrderStatus, int]:
        result = await self.db.execute(select(Order.status, func.count()).group_by(Order.status))
        return {status: count for status, count in result.all()}

    async def top_products(self, limit: int) -> list[tuple[uuid.UUID, str, str, int, Decimal]]:
        stmt = (
            select(
                Product.id,
                Product.name,
                Product.sku,
                func.sum(OrderItem.quantity).label("units_sold"),
                func.sum(OrderItem.line_total).label("revenue"),
            )
            .join(OrderItem, OrderItem.product_id == Product.id)
            .join(Sale, Sale.order_id == OrderItem.order_id)
            .group_by(Product.id, Product.name, Product.sku)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return [tuple(row) for row in result.all()]

    async def customer_count(self) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(User).where(User.role == UserRole.CUSTOMER)
        )
        return int(result.scalar_one())

    async def product_count(self) -> int:
        result = await self.db.execute(select(func.count()).select_from(Product))
        return int(result.scalar_one())
