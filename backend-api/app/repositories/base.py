"""Generic async repository providing common CRUD operations on top of
SQLAlchemy 2.x. Entity-specific repositories subclass this and add queries
that don't fit the generic shape (lookups by unique field, joined loads,
locking reads, etc.)."""

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base_class import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: type[ModelType], db: AsyncSession) -> None:
        self.model = model
        self.db = db

    async def get(self, id_: uuid.UUID) -> ModelType | None:
        return await self.db.get(self.model, id_)

    async def count(self, *, filters: list[Any] | None = None) -> int:
        stmt = select(func.count()).select_from(self.model)
        if filters:
            stmt = stmt.where(*filters)
        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    async def create(self, obj_in: dict[str, Any]) -> ModelType:
        obj = self.model(**obj_in)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: ModelType, obj_in: dict[str, Any]) -> ModelType:
        for field, value in obj_in.items():
            setattr(obj, field, value)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: ModelType) -> None:
        await self.db.delete(obj)
        await self.db.flush()

    # Defined last: this method's own name shadows the builtin `list` for
    # any code below it in the class body, so nothing here may use a bare
    # `list[...]` annotation after this point.
    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        filters: list[Any] | None = None,
        order_by: Any | None = None,
    ) -> list[ModelType]:
        stmt = select(self.model)
        if filters:
            stmt = stmt.where(*filters)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
