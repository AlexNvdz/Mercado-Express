import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order
from app.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Order, db)

    async def get_with_items(self, order_id: uuid.UUID) -> Order | None:
        result = await self.db.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items), selectinload(Order.shipping_address))
        )
        return result.scalar_one_or_none()

    async def get_by_order_number(self, order_number: str) -> Order | None:
        result = await self.db.execute(select(Order).where(Order.order_number == order_number))
        return result.scalar_one_or_none()

    async def list_for_customer(
        self, customer_id: uuid.UUID, *, offset: int = 0, limit: int = 20
    ) -> list[Order]:
        result = await self.db.execute(
            select(Order)
            .where(Order.customer_id == customer_id)
            .options(selectinload(Order.items), selectinload(Order.shipping_address))
            .order_by(Order.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_all(self, *, offset: int = 0, limit: int = 20) -> list[Order]:
        """Staff-only "every order" listing (see OrderService.list_all).
        Same shape as list_for_customer minus the customer filter -- items
        and shipping_address must be eager-loaded here too: OrderOut
        serializes both, and the generic BaseRepository.list() this used to
        call doesn't load either relationship, so accessing them during
        Pydantic validation triggered an async lazy-load outside the
        request's greenlet context (`MissingGreenlet`) instead of a normal
        500 with a clear cause.
        """
        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items), selectinload(Order.shipping_address))
            .order_by(Order.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())
