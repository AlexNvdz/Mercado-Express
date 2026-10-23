import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ConflictError, NotFoundError
from app.models.category import Category
from app.models.product import Product
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.category import CategoryCreate, CategoryUpdate


class CategoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = CategoryRepository(db)
        self.products = ProductRepository(db)

    async def create(self, data: CategoryCreate) -> Category:
        if await self.repo.get_by_name(data.name) is not None:
            raise ConflictError(f"Category '{data.name}' already exists.")
        category = await self.repo.create(data.model_dump())
        return await self.get(category.id)

    async def get(self, category_id: uuid.UUID) -> Category:
        """With `active_product_count` filled in, like every category this
        service returns."""
        category = await self.repo.get_with_count(category_id)
        if category is None:
            raise NotFoundError(f"Category {category_id} not found.")
        return category

    async def list(
        self, *, offset: int, limit: int, with_products: bool = False, sort_by_products: bool = False
    ) -> tuple[list[Category], int]:
        """`with_products`: only categories with at least one active product.
        `sort_by_products`: most active products first (then name) instead of
        by name."""
        return await self.repo.list_with_counts(
            offset=offset, limit=limit, with_products=with_products, sort_by_products=sort_by_products
        )

    async def update(self, category_id: uuid.UUID, data: CategoryUpdate) -> Category:
        category = await self.get(category_id)
        updates = data.model_dump(exclude_unset=True)
        new_name = updates.get("name")
        name_taken = (
            new_name is not None
            and new_name != category.name
            and await self.repo.get_by_name(new_name) is not None
        )
        if name_taken:
            raise ConflictError(f"Category '{new_name}' already exists.")
        await self.repo.update(category, updates)
        # The flush expired active_product_count (a query expression): reload it.
        return await self.get(category_id)

    async def delete(self, category_id: uuid.UUID) -> None:
        category = await self.get(category_id)
        # products.category_id is NOT NULL: without this check the ORM tries
        # to null it out on delete and the request fails with a 500.
        # Subcategories need no check -- their parent_id is simply cleared.
        product_count = await self.products.count(filters=[Product.category_id == category_id])
        if product_count:
            raise ConflictError(
                f"Category {category_id} still has {product_count} product(s); move or delete them first."
            )
        await self.repo.delete(category)
