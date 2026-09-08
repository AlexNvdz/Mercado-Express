import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment
from app.repositories.base import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Payment, db)

    async def list_for_order(self, order_id: uuid.UUID) -> list[Payment]:
        result = await self.db.execute(select(Payment).where(Payment.order_id == order_id))
        return list(result.scalars().all())
