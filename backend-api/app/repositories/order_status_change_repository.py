import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import OrderStatus, OrderStatusChangeSource
from app.models.order_status_change import OrderStatusChange
from app.repositories.base import BaseRepository


class OrderStatusChangeRepository(BaseRepository[OrderStatusChange]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(OrderStatusChange, db)

    async def record(
        self,
        *,
        order_id: uuid.UUID,
        from_status: OrderStatus | None,
        to_status: OrderStatus,
        source: OrderStatusChangeSource,
        actor_id: uuid.UUID | None,
    ) -> None:
        self.db.add(
            OrderStatusChange(
                order_id=order_id,
                from_status=from_status,
                to_status=to_status,
                source=source,
                actor_id=actor_id,
            )
        )
        await self.db.flush()

    async def list_for_order(self, order_id: uuid.UUID) -> list[OrderStatusChange]:
        """Oldest first, with `actor` eager-loaded (the response serializes it)."""
        result = await self.db.execute(
            select(OrderStatusChange)
            .where(OrderStatusChange.order_id == order_id)
            .options(selectinload(OrderStatusChange.actor))
            .order_by(OrderStatusChange.created_at)
        )
        return list(result.scalars().all())
