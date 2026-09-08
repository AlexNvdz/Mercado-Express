import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import require_staff
from app.schemas.inventory import InventoryAdjust, InventoryOut, InventorySetLevel
from app.services.inventory_service import InventoryService

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/{product_id}", response_model=InventoryOut)
async def get_inventory(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> InventoryOut:
    """Public: check availability for a product (e.g. to show 'in stock' on the storefront)."""
    inventory = await InventoryService(db).get_for_product(product_id)
    return InventoryOut(
        id=inventory.id,
        product_id=inventory.product_id,
        quantity_on_hand=inventory.quantity_on_hand,
        quantity_reserved=inventory.quantity_reserved,
        quantity_available=inventory.quantity_available,
        reorder_level=inventory.reorder_level,
        updated_at=inventory.updated_at,
    )


@router.post("/{product_id}/adjust", response_model=InventoryOut, dependencies=[Depends(require_staff)])
async def adjust_inventory(
    product_id: uuid.UUID, data: InventoryAdjust, db: AsyncSession = Depends(get_db)
) -> InventoryOut:
    """Staff/admin only: add or remove stock (restock, shrinkage, correction)."""
    inventory = await InventoryService(db).adjust_stock(product_id, data.delta)
    return InventoryOut(
        id=inventory.id,
        product_id=inventory.product_id,
        quantity_on_hand=inventory.quantity_on_hand,
        quantity_reserved=inventory.quantity_reserved,
        quantity_available=inventory.quantity_available,
        reorder_level=inventory.reorder_level,
        updated_at=inventory.updated_at,
    )


@router.put("/{product_id}", response_model=InventoryOut, dependencies=[Depends(require_staff)])
async def set_inventory_levels(
    product_id: uuid.UUID, data: InventorySetLevel, db: AsyncSession = Depends(get_db)
) -> InventoryOut:
    """Staff/admin only: set absolute stock/reorder levels."""
    inventory = await InventoryService(db).set_levels(
        product_id, data.quantity_on_hand, data.reorder_level
    )
    return InventoryOut(
        id=inventory.id,
        product_id=inventory.product_id,
        quantity_on_hand=inventory.quantity_on_hand,
        quantity_reserved=inventory.quantity_reserved,
        quantity_available=inventory.quantity_available,
        reorder_level=inventory.reorder_level,
        updated_at=inventory.updated_at,
    )
