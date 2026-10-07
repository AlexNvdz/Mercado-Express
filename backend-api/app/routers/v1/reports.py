from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import require_staff
from app.schemas.report import ReportSummary
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"], dependencies=[Depends(require_staff)])


@router.get("/summary", response_model=ReportSummary)
async def get_report_summary(
    top_products_limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> ReportSummary:
    """Staff/admin only: net/gross/refunded revenue, order counts by status,
    top products by units sold, and customer/product counts -- computed
    server-side from the Sale ledger, not from Order.total_amount."""
    return await ReportService(db).summary(top_products_limit=top_products_limit)
