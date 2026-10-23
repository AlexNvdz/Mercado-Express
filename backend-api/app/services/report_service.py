import time
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.enums import OrderStatus
from app.repositories.report_repository import ReportRepository
from app.schemas.report import OrderStatusCount, ReportSummary, TopProduct

_TWO_PLACES = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    # An empty ledger sums to a bare 0; money fields are always 2dp strings.
    return value.quantize(_TWO_PLACES)


# top_products_limit -> (time.monotonic() when computed, summary).
# shortcut: per-process memory and expiry only (no invalidation on writes),
# so a change shows up within REPORT_CACHE_SECONDS; with several workers each
# keeps its own copy. Move to a shared cache (Redis) if that ever matters.
_cache: dict[int, tuple[float, ReportSummary]] = {}


class ReportService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = ReportRepository(db)

    async def summary(self, *, top_products_limit: int = 10) -> ReportSummary:
        """Cached for settings.REPORT_CACHE_SECONDS; `generated_at` says when
        it was computed."""
        cached = _cache.get(top_products_limit)
        if cached is not None and time.monotonic() - cached[0] < settings.REPORT_CACHE_SECONDS:
            return cached[1]
        summary = await self._compute(top_products_limit)
        if settings.REPORT_CACHE_SECONDS > 0:
            _cache[top_products_limit] = (time.monotonic(), summary)
        return summary

    async def _compute(self, top_products_limit: int) -> ReportSummary:
        totals = await self.repo.ledger_totals()
        status_counts = await self.repo.order_counts_by_status()
        top_rows = await self.repo.top_products(top_products_limit)
        customer_count = await self.repo.customer_count()
        product_count = await self.repo.product_count()

        return ReportSummary(
            net_revenue=_money(totals.gross_revenue - totals.refunded_amount),
            gross_revenue=_money(totals.gross_revenue),
            refunded_amount=_money(totals.refunded_amount),
            sale_count=totals.sale_count,
            reversal_count=totals.reversal_count,
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
