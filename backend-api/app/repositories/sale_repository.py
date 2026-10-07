import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SaleKind
from app.models.sale import Sale
from app.repositories.base import BaseRepository


class SaleRepository(BaseRepository[Sale]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Sale, db)

    async def get_for_order(self, order_id: uuid.UUID, kind: SaleKind) -> Sale | None:
        result = await self.db.execute(select(Sale).where(Sale.order_id == order_id, Sale.kind == kind))
        return result.scalar_one_or_none()
