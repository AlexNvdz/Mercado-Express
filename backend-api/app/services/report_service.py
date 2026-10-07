from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import OrderStatus
from app.repositories.report_repository import ReportRepository
from app.schemas.report import OrderStatusCount, ReportSummary, TopProduct


class ReportService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = ReportRepository(db)

    async def summary(self, *, top_products_limit: int = 10) -> ReportSummary:
        revenue = await self.repo.total_revenue()
        sale_count = await self.repo.sale_count()
        status_counts = await self.repo.order_counts_by_status()
        top_rows = await self.repo.top_products(top_products_limit)
        customer_count = await self.repo.customer_count()
        product_count = await self.repo.product_count()

        return ReportSummary(
            total_revenue=revenue,
            sale_count=sale_count,
            orders_by_status=[
                OrderStatusCount(status=status, count=status_counts.get(status, 0)) for status in OrderStatus
            ],
            top_products=[
                TopProduct(product_id=pid, name=name, sku=sku, units_sold=int(units), revenue=rev)
                for pid, name, sku, units, rev in top_rows
            ],
            customer_count=customer_count,
            product_count=product_count,
            generated_at=datetime.now(UTC),
        )
