"""Inventory repository.

Stock mutations (`reserve`, `release`, `adjust`) use `SELECT ... FOR UPDATE`
to lock the row for the duration of the transaction, so concurrent order
placements can't oversell the same product.
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import InsufficientStockError, NotFoundError
from app.models.inventory import Inventory
from app.models.product import Product
from app.repositories.base import BaseRepository

# Shared predicate for "needs restocking": available stock at or below the
# product's own reorder level.
_LOW_STOCK = Inventory.quantity_on_hand - Inventory.quantity_reserved <= Inventory.reorder_level
# Rows of products still on sale. A subquery rather than a join, so the
# same predicate also works in BaseRepository.count().
_ACTIVE_PRODUCT = Inventory.product_id.in_(select(Product.id).where(Product.is_active.is_(True)))


class InventoryRepository(BaseRepository[Inventory]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Inventory, db)

    async def get_by_product_id(self, product_id: uuid.UUID) -> Inventory | None:
        result = await self.db.execute(select(Inventory).where(Inventory.product_id == product_id))
        return result.scalar_one_or_none()

    @staticmethod
    def _filters(*, low_stock: bool, include_inactive: bool) -> list[Any]:
        filters: list[Any] = []
        if low_stock:
            filters.append(_LOW_STOCK)
        if not include_inactive:
            filters.append(_ACTIVE_PRODUCT)
        return filters

    async def list_filtered(
        self, *, offset: int = 0, limit: int = 20, low_stock: bool = False, include_inactive: bool = False
    ) -> list[Inventory]:
        stmt = select(Inventory).where(*self._filters(low_stock=low_stock, include_inactive=include_inactive))
        stmt = stmt.order_by(Inventory.updated_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_filtered(self, *, low_stock: bool = False, include_inactive: bool = False) -> int:
        return await self.count(filters=self._filters(low_stock=low_stock, include_inactive=include_inactive))

    async def get_by_product_id_locked(self, product_id: uuid.UUID) -> Inventory:
        result = await self.db.execute(
            select(Inventory).where(Inventory.product_id == product_id).with_for_update()
        )
        inventory = result.scalar_one_or_none()
        if inventory is None:
            raise NotFoundError(f"No inventory record for product {product_id}.")
        return inventory

    async def reserve(self, product_id: uuid.UUID, quantity: int) -> Inventory:
        inventory = await self.get_by_product_id_locked(product_id)
        if inventory.quantity_available < quantity:
            raise InsufficientStockError(
                f"Insufficient stock for product {product_id}: "
                f"requested {quantity}, available {inventory.quantity_available}."
            )
        inventory.quantity_reserved += quantity
        await self.db.flush()
        await self.db.refresh(inventory)
        return inventory

    async def release(self, product_id: uuid.UUID, quantity: int) -> Inventory:
        inventory = await self.get_by_product_id_locked(product_id)
        inventory.quantity_reserved = max(0, inventory.quantity_reserved - quantity)
        await self.db.flush()
        await self.db.refresh(inventory)
        return inventory

    async def fulfill(self, product_id: uuid.UUID, quantity: int) -> Inventory:
        """Convert a reservation into an actual stock decrement (on shipment)."""
        inventory = await self.get_by_product_id_locked(product_id)
        inventory.quantity_reserved = max(0, inventory.quantity_reserved - quantity)
        inventory.quantity_on_hand = max(0, inventory.quantity_on_hand - quantity)
        await self.db.flush()
        await self.db.refresh(inventory)
        return inventory

    async def adjust(self, product_id: uuid.UUID, delta: int) -> Inventory:
        inventory = await self.get_by_product_id_locked(product_id)
        new_qty = inventory.quantity_on_hand + delta
        if new_qty < inventory.quantity_reserved:
            raise InsufficientStockError(
                f"Cannot reduce stock below reserved quantity "
                f"({inventory.quantity_reserved}) for product {product_id}."
            )
        inventory.quantity_on_hand = new_qty
        await self.db.flush()
        await self.db.refresh(inventory)
        return inventory
