import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import PaginationParams, pagination_params, require_staff
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from app.schemas.common import Page
from app.services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post(
    "",
    response_model=CategoryOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_staff)],
)
async def create_category(data: CategoryCreate, db: AsyncSession = Depends(get_db)) -> CategoryOut:
    category = await CategoryService(db).create(data)
    return CategoryOut.model_validate(category)


@router.get("", response_model=Page[CategoryOut])
async def list_categories(
    pagination: PaginationParams = Depends(pagination_params), db: AsyncSession = Depends(get_db)
) -> Page[CategoryOut]:
    items, total = await CategoryService(db).list(offset=pagination.offset, limit=pagination.page_size)
    pages = (total + pagination.page_size - 1) // pagination.page_size if total else 0
    return Page(
        items=[CategoryOut.model_validate(i) for i in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=pages,
    )


@router.get("/{category_id}", response_model=CategoryOut)
async def get_category(category_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> CategoryOut:
    category = await CategoryService(db).get(category_id)
    return CategoryOut.model_validate(category)


@router.patch("/{category_id}", response_model=CategoryOut, dependencies=[Depends(require_staff)])
async def update_category(
    category_id: uuid.UUID, data: CategoryUpdate, db: AsyncSession = Depends(get_db)
) -> CategoryOut:
    category = await CategoryService(db).update(category_id, data)
    return CategoryOut.model_validate(category)


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_staff)],
)
async def delete_category(category_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    await CategoryService(db).delete(category_id)
