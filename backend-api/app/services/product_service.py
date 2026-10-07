import uuid

from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ConflictError, NotFoundError
from app.models.inventory import Inventory
from app.models.product import Product
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate
from app.services.storage_service import ImageStorage, LocalDiskImageStorage


class ProductService:
    def __init__(self, db: AsyncSession, storage: ImageStorage | None = None) -> None:
        self.db = db
        self.repo = ProductRepository(db)
        self.categories = CategoryRepository(db)
        self.storage = storage or LocalDiskImageStorage()

    async def create(self, data: ProductCreate) -> Product:
        if await self.repo.get_by_sku(data.sku) is not None:
            raise ConflictError(f"SKU '{data.sku}' already exists.")
        if await self.categories.get(data.category_id) is None:
            raise NotFoundError(f"Category {data.category_id} not found.")

        product = await self.repo.create(data.model_dump())
        # Every product gets an inventory record at creation time (starts at zero).
        self.db.add(Inventory(product_id=product.id, quantity_on_hand=0, quantity_reserved=0))
        await self.db.flush()
        # Re-fetch with `images` eager-loaded (empty list) -- accessing the
        # unloaded relationship on `product` directly would try an implicit
        # lazy load, which AsyncSession doesn't allow outside an await.
        return await self.get(product.id)

    async def get(self, product_id: uuid.UUID) -> Product:
        product = await self.repo.get_with_images(product_id)
        if product is None:
            raise NotFoundError(f"Product {product_id} not found.")
        return product

    async def list(
        self,
        *,
        offset: int,
        limit: int,
        category_id: uuid.UUID | None = None,
        search: str | None = None,
        active_only: bool = True,
    ) -> tuple[list[Product], int]:
        filters = []
        if category_id is not None:
            filters.append(Product.category_id == category_id)
        if active_only:
            filters.append(Product.is_active.is_(True))
        if search:
            pattern = f"%{search.strip()}%"
            filters.append(or_(Product.name.ilike(pattern), Product.sku.ilike(pattern)))
        items = await self.repo.list_with_images(
            offset=offset, limit=limit, filters=filters, order_by=Product.name
        )
        total = await self.repo.count(filters=filters)
        return items, total

    async def update(self, product_id: uuid.UUID, data: ProductUpdate) -> Product:
        product = await self.get(product_id)
        updates = data.model_dump(exclude_unset=True)
        new_sku = updates.get("sku")
        sku_taken = (
            new_sku is not None and new_sku != product.sku and await self.repo.get_by_sku(new_sku) is not None
        )
        if sku_taken:
            raise ConflictError(f"SKU '{new_sku}' already exists.")
        if "category_id" in updates and await self.categories.get(updates["category_id"]) is None:
            raise NotFoundError(f"Category {updates['category_id']} not found.")
        return await self.repo.update(product, updates)

    async def delete(self, product_id: uuid.UUID) -> None:
        product = await self.get(product_id)
        await self.repo.delete(product)
        # Image rows are gone via cascade; purge their files from disk too --
        # this is the only point where product image files are ever removed.
        self.storage.delete_product_files(product_id)
