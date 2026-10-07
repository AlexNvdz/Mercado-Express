import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import InventoryChangeKind
from app.models.inventory import Inventory
from app.models.inventory_change import InventoryChange
from app.repositories.base import BaseRepository


class InventoryChangeRepository(BaseRepository[InventoryChange]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(InventoryChange, db)

    async def record(
        self,
        *,
        kind: InventoryChangeKind,
        before: tuple[int, int],
        after: Inventory,
        reason: str | None,
        actor_id: uuid.UUID | None,
    ) -> None:
        """`before` is (quantity_on_hand, reorder_level) read under the row
        lock, ahead of the change; `after` is the updated inventory row."""
        on_hand_before, reorder_level_before = before
        self.db.add(
            InventoryChange(
                product_id=after.product_id,
                kind=kind,
                quantity_on_hand_before=on_hand_before,
                quantity_on_hand_after=after.quantity_on_hand,
                reorder_level_before=reorder_level_before,
                reorder_level_after=after.reorder_level,
                reason=reason,
                actor_id=actor_id,
            )
        )
        await self.db.flush()

    async def list_for_product(
        self, product_id: uuid.UUID, *, offset: int, limit: int
    ) -> list[InventoryChange]:
        """Newest first, with `actor` eager-loaded (the response serializes it)."""
        result = await self.db.execute(
            select(InventoryChange)
            .where(InventoryChange.product_id == product_id)
            .options(selectinload(InventoryChange.actor))
            .order_by(InventoryChange.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_for_product(self, product_id: uuid.UUID) -> int:
        return await self.count(filters=[InventoryChange.product_id == product_id])
