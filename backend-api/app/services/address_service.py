import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.address import Address
from app.repositories.address_repository import AddressRepository
from app.schemas.address import AddressCreate, AddressUpdate


class AddressService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = AddressRepository(db)

    async def create(self, user_id: uuid.UUID, data: AddressCreate) -> Address:
        return await self.repo.create({**data.model_dump(), "user_id": user_id})

    async def list_for_user(self, user_id: uuid.UUID) -> list[Address]:
        return await self.repo.list_for_user(user_id)

    async def get_for_user(self, user_id: uuid.UUID, address_id: uuid.UUID) -> Address:
        address = await self.repo.get(address_id)
        if address is None or address.user_id != user_id:
            raise NotFoundError(f"Address {address_id} not found.")
        return address

    async def update(self, user_id: uuid.UUID, address_id: uuid.UUID, data: AddressUpdate) -> Address:
        address = await self.get_for_user(user_id, address_id)
        return await self.repo.update(address, data.model_dump(exclude_unset=True))

    async def delete(self, user_id: uuid.UUID, address_id: uuid.UUID) -> None:
        address = await self.get_for_user(user_id, address_id)
        await self.repo.delete(address)
