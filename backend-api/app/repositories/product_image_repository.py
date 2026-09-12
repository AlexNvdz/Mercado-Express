import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product_image import ProductImage
from app.repositories.base import BaseRepository


class ProductImageRepository(BaseRepository[ProductImage]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(ProductImage, db)

    async def list_for_product(self, product_id: uuid.UUID) -> list[ProductImage]:
        result = await self.db.execute(
            select(ProductImage)
            .where(ProductImage.product_id == product_id)
            .order_by(ProductImage.position)
        )
        return list(result.scalars().all())
