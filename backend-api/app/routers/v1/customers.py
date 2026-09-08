import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import PaginationParams, get_current_user, pagination_params, require_staff
from app.models.user import User
from app.schemas.address import AddressCreate, AddressOut, AddressUpdate
from app.schemas.common import Page
from app.schemas.customer import CustomerOut, CustomerUpdate
from app.services.address_service import AddressService
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("/me", response_model=CustomerOut)
async def read_my_profile(current_user: User = Depends(get_current_user)) -> CustomerOut:
    return CustomerOut.model_validate(current_user)


@router.patch("/me", response_model=CustomerOut)
async def update_my_profile(
    data: CustomerUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomerOut:
    updated = await CustomerService(db).update(current_user.id, data)
    return CustomerOut.model_validate(updated)


@router.get("/me/addresses", response_model=list[AddressOut])
async def list_my_addresses(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[AddressOut]:
    addresses = await AddressService(db).list_for_user(current_user.id)
    return [AddressOut.model_validate(a) for a in addresses]


@router.post("/me/addresses", response_model=AddressOut, status_code=status.HTTP_201_CREATED)
async def create_my_address(
    data: AddressCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AddressOut:
    address = await AddressService(db).create(current_user.id, data)
    return AddressOut.model_validate(address)


@router.patch("/me/addresses/{address_id}", response_model=AddressOut)
async def update_my_address(
    address_id: uuid.UUID,
    data: AddressUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AddressOut:
    address = await AddressService(db).update(current_user.id, address_id, data)
    return AddressOut.model_validate(address)


@router.delete("/me/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_address(
    address_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await AddressService(db).delete(current_user.id, address_id)


@router.get("", response_model=Page[CustomerOut], dependencies=[Depends(require_staff)])
async def list_customers(
    pagination: PaginationParams = Depends(pagination_params), db: AsyncSession = Depends(get_db)
) -> Page[CustomerOut]:
    items, total = await CustomerService(db).list(offset=pagination.offset, limit=pagination.page_size)
    pages = (total + pagination.page_size - 1) // pagination.page_size if total else 0
    return Page(
        items=[CustomerOut.model_validate(i) for i in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=pages,
    )


@router.get("/{customer_id}", response_model=CustomerOut, dependencies=[Depends(require_staff)])
async def get_customer(customer_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> CustomerOut:
    customer = await CustomerService(db).get(customer_id)
    return CustomerOut.model_validate(customer)
