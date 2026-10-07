import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import InsufficientStockError, NotFoundError
from app.models.enums import InventoryChangeKind
from app.models.inventory import Inventory
from app.models.inventory_change import InventoryChange
from app.repositories.inventory_change_repository import InventoryChangeRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.product_repository import ProductRepository


class InventoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = InventoryRepository(db)
        self.products = ProductRepository(db)
        self.changes = InventoryChangeRepository(db)

    async def _ensure_product(self, product_id: uuid.UUID) -> None:
        if await self.products.get(product_id) is None:
            raise NotFoundError(f"Product {product_id} not found.")

    async def get_for_product(self, product_id: uuid.UUID) -> Inventory:
        await self._ensure_product(product_id)
        inventory = await self.repo.get_by_product_id(product_id)
        if inventory is None:
            raise NotFoundError(f"No inventory record for product {product_id}.")
        return inventory

    async def adjust_stock(
        self, product_id: uuid.UUID, delta: int, *, reason: str | None, actor_id: uuid.UUID | None
    ) -> Inventory:
        await self._ensure_product(product_id)
        locked = await self.repo.get_by_product_id_locked(product_id)
        before = (locked.quantity_on_hand, locked.reorder_level)
        inventory = await self.repo.adjust(product_id, delta)
        await self.changes.record(
            kind=InventoryChangeKind.ADJUST, before=before, after=inventory, reason=reason, actor_id=actor_id
        )
        return inventory

    async def set_levels(
        self,
        product_id: uuid.UUID,
        quantity_on_hand: int,
        reorder_level: int | None,
        *,
        reason: str | None,
        actor_id: uuid.UUID | None,
    ) -> Inventory:
        await self._ensure_product(product_id)
        inventory = await self.repo.get_by_product_id_locked(product_id)
        if quantity_on_hand < inventory.quantity_reserved:
            raise InsufficientStockError(
                f"Cannot set stock below reserved quantity "
                f"({inventory.quantity_reserved}) for product {product_id}."
            )
        before = (inventory.quantity_on_hand, inventory.reorder_level)
        updates: dict = {"quantity_on_hand": quantity_on_hand}
        if reorder_level is not None:
            updates["reorder_level"] = reorder_level
        inventory = await self.repo.update(inventory, updates)
        await self.changes.record(
            kind=InventoryChangeKind.SET_LEVELS,
            before=before,
            after=inventory,
            reason=reason,
            actor_id=actor_id,
        )
        return inventory

    async def history(
        self, product_id: uuid.UUID, *, offset: int, limit: int
    ) -> tuple[list[InventoryChange], int]:
        await self._ensure_product(product_id)
        items = await self.changes.list_for_product(product_id, offset=offset, limit=limit)
        total = await self.changes.count_for_product(product_id)
        return items, total

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

    # Defined last: this method's own name shadows the builtin `list` for
    # any annotation below it in the class body (same as BaseRepository).
    async def list(
        self, *, offset: int, limit: int, low_stock: bool = False, include_inactive: bool = False
    ) -> tuple[list[Inventory], int]:
        """Batched read for dashboards (e.g. low-stock alerts) -- avoids
        callers paging `GET /inventory/{id}` once per product. Rows of
        inactive products are left out unless `include_inactive`."""
        items = await self.repo.list_filtered(
            offset=offset, limit=limit, low_stock=low_stock, include_inactive=include_inactive
        )
        total = await self.repo.count_filtered(low_stock=low_stock, include_inactive=include_inactive)
        return items, total
