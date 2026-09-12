"""Product image management: upload and delete of ProductImage rows, backed
by an ImageStorage port (see app/services/storage_service.py). Physical file
removal only happens when the whole product is deleted -- see
ProductService.delete."""

import uuid

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.product_image import ProductImage
from app.repositories.product_image_repository import ProductImageRepository
from app.repositories.product_repository import ProductRepository
from app.services.storage_service import ImageStorage, LocalDiskImageStorage


class ProductImageService:
    def __init__(self, db: AsyncSession, storage: ImageStorage | None = None) -> None:
        self.db = db
        self.repo = ProductImageRepository(db)
        self.products = ProductRepository(db)
        self.storage = storage or LocalDiskImageStorage()

    async def add(self, product_id: uuid.UUID, upload: UploadFile) -> ProductImage:
        if await self.products.get(product_id) is None:
            raise NotFoundError(f"Product {product_id} not found.")
        existing = await self.repo.list_for_product(product_id)
        file_path = await self.storage.save(product_id, upload)
        return await self.repo.create(
            {"product_id": product_id, "file_path": file_path, "position": len(existing)}
        )

    async def delete(self, product_id: uuid.UUID, image_id: uuid.UUID) -> None:
        """Removes the ProductImage row only -- the file stays on disk until
        the whole product is deleted (see ProductService.delete)."""
        image = await self.repo.get(image_id)
        if image is None or image.product_id != product_id:
            raise NotFoundError(f"Image {image_id} not found for product {product_id}.")
        await self.repo.delete(image)
