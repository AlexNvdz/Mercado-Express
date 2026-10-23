import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import PaginationParams, pagination_params, require_staff
from app.models.inventory import Inventory
from app.models.user import User
from app.schemas.common import Page
from app.schemas.inventory import (
    InventoryAdjust,
    InventoryChangeOut,
    InventoryListItem,
    InventoryOut,
    InventorySetLevel,
)
from app.services.inventory_service import InventoryService

router = APIRouter(prefix="/inventory", tags=["inventory"])

# One page of products on screen at most (MAX_PAGE_SIZE); keeps the IN list short.
_MAX_PRODUCT_IDS = 100


def _out(inventory: Inventory) -> InventoryOut:
    return InventoryOut(
        id=inventory.id,
        product_id=inventory.product_id,
        quantity_on_hand=inventory.quantity_on_hand,
        quantity_reserved=inventory.quantity_reserved,
        quantity_available=inventory.quantity_available,
        reorder_level=inventory.reorder_level,
        updated_at=inventory.updated_at,
    )


@router.get("", response_model=Page[InventoryListItem], dependencies=[Depends(require_staff)])
async def list_inventory(
    low_stock: bool = Query(
        default=False, description="Only return items where quantity_available <= reorder_level."
    ),
    include_inactive: bool = Query(
        default=False, description="Also return rows of inactive products (left out by default)."
    ),
    product_ids: list[uuid.UUID] | None = Query(
        default=None,
        alias="product_id",
        max_length=_MAX_PRODUCT_IDS,
        description=f"Only these products; repeat it for several (at most {_MAX_PRODUCT_IDS}): "
        "?product_id=...&product_id=...",
    ),
    search: str | None = Query(
        default=None, max_length=100, description="Case-insensitive match on product name or SKU."
    ),
    pagination: PaginationParams = Depends(pagination_params),
    db: AsyncSession = Depends(get_db),
) -> Page[InventoryListItem]:
    """Staff/admin only: batched inventory read (e.g. for a low-stock
    dashboard alert) -- replaces paging GET /inventory/{id} once per product."""
    items, total = await InventoryService(db).list(
        offset=pagination.offset,
        limit=pagination.page_size,
        low_stock=low_stock,
        include_inactive=include_inactive,
        product_ids=product_ids,
        search=search,
    )
    pages = (total + pagination.page_size - 1) // pagination.page_size if total else 0
    return Page(
        items=[InventoryListItem.model_validate(i) for i in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=pages,
    )


@router.get("/{product_id}", response_model=InventoryOut)
async def get_inventory(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> InventoryOut:
    """Public: check availability for a product (e.g. to show 'in stock' on the storefront)."""
    return _out(await InventoryService(db).get_for_product(product_id))


@router.get(
    "/{product_id}/history", response_model=Page[InventoryChangeOut], dependencies=[Depends(require_staff)]
)
async def get_inventory_history(
    product_id: uuid.UUID,
    pagination: PaginationParams = Depends(pagination_params),
    db: AsyncSession = Depends(get_db),
) -> Page[InventoryChangeOut]:
    """Staff/admin only: manual stock changes (adjust, set levels) of a
    product, newest first -- who, why, and the values before and after."""
    items, total = await InventoryService(db).history(
        product_id, offset=pagination.offset, limit=pagination.page_size
    )
    pages = (total + pagination.page_size - 1) // pagination.page_size if total else 0
    return Page(
        items=[InventoryChangeOut.model_validate(i) for i in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=pages,
    )


@router.post("/{product_id}/adjust", response_model=InventoryOut)
async def adjust_inventory(
    product_id: uuid.UUID,
    data: InventoryAdjust,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> InventoryOut:
    """Staff/admin only: add or remove stock (restock, shrinkage, correction)."""
    inventory = await InventoryService(db).adjust_stock(
        product_id, data.delta, reason=data.reason, actor_id=current_user.id
    )
    return _out(inventory)


@router.put("/{product_id}", response_model=InventoryOut)
async def set_inventory_levels(
    product_id: uuid.UUID,
    data: InventorySetLevel,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> InventoryOut:
    """Staff/admin only: set absolute stock/reorder levels."""
    inventory = await InventoryService(db).set_levels(
        product_id, data.quantity_on_hand, data.reorder_level, reason=data.reason, actor_id=current_user.id
    )
    return _out(inventory)
