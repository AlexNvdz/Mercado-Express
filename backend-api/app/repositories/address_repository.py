import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.address import Address
from app.repositories.base import BaseRepository


class AddressRepository(BaseRepository[Address]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Address, db)

    async def list_for_user(self, user_id: uuid.UUID) -> list[Address]:
        result = await self.db.execute(select(Address).where(Address.user_id == user_id))
        return list(result.scalars().all())
