"""Read-only aggregate queries backing GET /reports/summary.

Revenue and per-product units sold are computed from the append-only
`sales` ledger (joined to `order_items`), never from `Order.total_amount`.
A paid order has a `sale` entry; if it is later cancelled or refunded it
also gets a negative `reversal` entry, so revenue is net of returns and
reversed orders drop out of the top-products ranking.
"""

import uuid
from decimal import Decimal
from typing import NamedTuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import OrderStatus, SaleKind, UserRole
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.sale import Sale
from app.models.user import User


class LedgerTotals(NamedTuple):
    gross_revenue: Decimal
    refunded_amount: Decimal  # positive: the reversal entries negated
    sale_count: int
    reversal_count: int


class ReportRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def ledger_totals(self) -> LedgerTotals:
        is_sale = Sale.kind == SaleKind.SALE
        is_reversal = Sale.kind == SaleKind.REVERSAL
        result = await self.db.execute(
            select(
                func.coalesce(func.sum(Sale.total_amount).filter(is_sale), 0),
                func.coalesce(-func.sum(Sale.total_amount).filter(is_reversal), 0),
                func.count().filter(is_sale),
                func.count().filter(is_reversal),
            )
        )
        gross, refunded, sale_count, reversal_count = result.one()
        return LedgerTotals(Decimal(gross), Decimal(refunded), int(sale_count), int(reversal_count))

    async def order_counts_by_status(self) -> dict[OrderStatus, int]:
        result = await self.db.execute(select(Order.status, func.count()).group_by(Order.status))
        return {status: count for status, count in result.all()}

    async def top_products(self, limit: int) -> list[tuple[uuid.UUID, str, str, int, Decimal]]:
        """Units and revenue from orders that were paid and not reversed."""
        reversed_orders = select(Sale.order_id).where(Sale.kind == SaleKind.REVERSAL)
        stmt = (
            select(
                Product.id,
                Product.name,
                Product.sku,
                func.sum(OrderItem.quantity).label("units_sold"),
                func.sum(OrderItem.line_total).label("revenue"),
            )
            .join(OrderItem, OrderItem.product_id == Product.id)
            .join(Sale, (Sale.order_id == OrderItem.order_id) & (Sale.kind == SaleKind.SALE))
            .where(OrderItem.order_id.not_in(reversed_orders))
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
