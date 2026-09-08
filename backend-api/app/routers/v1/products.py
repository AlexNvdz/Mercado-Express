import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import PaginationParams, pagination_params, require_staff
from app.schemas.common import Page
from app.schemas.product import ProductCreate, ProductOut, ProductUpdate
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])


@router.post(
    "",
    response_model=ProductOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_staff)],
)
async def create_product(data: ProductCreate, db: AsyncSession = Depends(get_db)) -> ProductOut:
    product = await ProductService(db).create(data)
    return ProductOut.model_validate(product)


@router.get("", response_model=Page[ProductOut])
async def list_products(
    category_id: uuid.UUID | None = None,
    pagination: PaginationParams = Depends(pagination_params),
    db: AsyncSession = Depends(get_db),
) -> Page[ProductOut]:
    items, total = await ProductService(db).list(
        offset=pagination.offset, limit=pagination.page_size, category_id=category_id
    )
    pages = (total + pagination.page_size - 1) // pagination.page_size if total else 0
    return Page(
        items=[ProductOut.model_validate(i) for i in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=pages,
    )


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> ProductOut:
    product = await ProductService(db).get(product_id)
    return ProductOut.model_validate(product)


@router.patch("/{product_id}", response_model=ProductOut, dependencies=[Depends(require_staff)])
async def update_product(
    product_id: uuid.UUID, data: ProductUpdate, db: AsyncSession = Depends(get_db)
) -> ProductOut:
    product = await ProductService(db).update(product_id, data)
    return ProductOut.model_validate(product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_staff)])
async def delete_product(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    await ProductService(db).delete(product_id)
