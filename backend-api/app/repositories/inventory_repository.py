"""Inventory repository.

Stock mutations (`reserve`, `release`, `adjust`) use `SELECT ... FOR UPDATE`
to lock the row for the duration of the transaction, so concurrent order
placements can't oversell the same product.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import InsufficientStockError, NotFoundError
from app.models.inventory import Inventory
from app.repositories.base import BaseRepository


class InventoryRepository(BaseRepository[Inventory]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Inventory, db)

    async def get_by_product_id(self, product_id: uuid.UUID) -> Inventory | None:
        result = await self.db.execute(
            select(Inventory).where(Inventory.product_id == product_id)
        )
        return result.scalar_one_or_none()

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
