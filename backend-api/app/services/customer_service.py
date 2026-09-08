import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.customer import CustomerUpdate


class CustomerService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = UserRepository(db)

    async def get(self, user_id: uuid.UUID) -> User:
        user = await self.repo.get(user_id)
        if user is None or user.role != UserRole.CUSTOMER:
            raise NotFoundError(f"Customer {user_id} not found.")
        return user

    async def list(self, *, offset: int, limit: int) -> tuple[list[User], int]:
        filters = [User.role == UserRole.CUSTOMER]
        items = await self.repo.list(
            offset=offset, limit=limit, filters=filters, order_by=User.created_at.desc()
        )
        total = await self.repo.count(filters=filters)
        return items, total

    async def update(self, user_id: uuid.UUID, data: CustomerUpdate) -> User:
        user = await self.get(user_id)
        return await self.repo.update(user, data.model_dump(exclude_unset=True))
