import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shipment import Shipment
from app.repositories.base import BaseRepository


class ShipmentRepository(BaseRepository[Shipment]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Shipment, db)

    async def get_by_order_id(self, order_id: uuid.UUID) -> Shipment | None:
        result = await self.db.execute(select(Shipment).where(Shipment.order_id == order_id))
        return result.scalar_one_or_none()
