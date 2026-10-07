import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order
from app.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Order, db)

    async def get_with_items(self, order_id: uuid.UUID, *, for_update: bool = False) -> Order | None:
        """`for_update=True` locks the order row (SELECT ... FOR UPDATE) until
        the transaction ends. Every status change takes this lock first, so
        two requests on the same order (e.g. a double-submitted "ship", or
        "ship" racing "cancel") run one after the other, and the second one
        sees the first one's result instead of acting on a stale status."""
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items), selectinload(Order.shipping_address))
        )
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_order_number(self, order_number: str) -> Order | None:
        result = await self.db.execute(select(Order).where(Order.order_number == order_number))
        return result.scalar_one_or_none()

    async def list_filtered(self, *, filters: list[Any], offset: int = 0, limit: int = 20) -> list[Order]:
        """Newest first, matching `filters` (see OrderService.list_orders).
        Items and shipping_address must be eager-loaded here: OrderOut
        serializes both, and the generic BaseRepository.list() doesn't load
        either relationship, so accessing them during Pydantic validation
        triggered an async lazy-load outside the request's greenlet context
        (`MissingGreenlet`) instead of a normal 500 with a clear cause.
        """
        result = await self.db.execute(
            select(Order)
            .where(*filters)
            .options(selectinload(Order.items), selectinload(Order.shipping_address))
            .order_by(Order.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())
