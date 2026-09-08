import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.inventory import Inventory
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.product_repository import ProductRepository


class InventoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = InventoryRepository(db)
        self.products = ProductRepository(db)

    async def get_for_product(self, product_id: uuid.UUID) -> Inventory:
        if await self.products.get(product_id) is None:
            raise NotFoundError(f"Product {product_id} not found.")
        inventory = await self.repo.get_by_product_id(product_id)
        if inventory is None:
            raise NotFoundError(f"No inventory record for product {product_id}.")
        return inventory

    async def adjust_stock(self, product_id: uuid.UUID, delta: int) -> Inventory:
        if await self.products.get(product_id) is None:
            raise NotFoundError(f"Product {product_id} not found.")
        return await self.repo.adjust(product_id, delta)

    async def set_levels(
        self, product_id: uuid.UUID, quantity_on_hand: int, reorder_level: int | None
    ) -> Inventory:
        inventory = await self.get_for_product(product_id)
        updates: dict = {"quantity_on_hand": quantity_on_hand}
        if reorder_level is not None:
            updates["reorder_level"] = reorder_level
        return await self.repo.update(inventory, updates)

    async def reserve(self, product_id: uuid.UUID, quantity: int) -> Inventory:
        """Reserve stock for a pending order. Raises InsufficientStockError if
        not enough is available."""
        return await self.repo.reserve(product_id, quantity)

    async def release(self, product_id: uuid.UUID, quantity: int) -> Inventory:
        """Release a previously made reservation (order cancelled/failed payment)."""
        return await self.repo.release(product_id, quantity)

    async def fulfill(self, product_id: uuid.UUID, quantity: int) -> Inventory:
        """Convert a reservation into a real stock decrement (on shipment)."""
        return await self.repo.fulfill(product_id, quantity)
