import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ConflictError, NotFoundError
from app.models.category import Category
from app.repositories.category_repository import CategoryRepository
from app.schemas.category import CategoryCreate, CategoryUpdate


class CategoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = CategoryRepository(db)

    async def create(self, data: CategoryCreate) -> Category:
        if await self.repo.get_by_name(data.name) is not None:
            raise ConflictError(f"Category '{data.name}' already exists.")
        return await self.repo.create(data.model_dump())

    async def get(self, category_id: uuid.UUID) -> Category:
        category = await self.repo.get(category_id)
        if category is None:
            raise NotFoundError(f"Category {category_id} not found.")
        return category

    async def list(self, *, offset: int, limit: int) -> tuple[list[Category], int]:
        items = await self.repo.list(offset=offset, limit=limit, order_by=Category.name)
        total = await self.repo.count()
        return items, total

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
        return await self.repo.update(category, updates)

    async def delete(self, category_id: uuid.UUID) -> None:
        category = await self.get(category_id)
        await self.repo.delete(category)
