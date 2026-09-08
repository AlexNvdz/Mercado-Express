from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sale import Sale
from app.repositories.base import BaseRepository


class SaleRepository(BaseRepository[Sale]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Sale, db)
