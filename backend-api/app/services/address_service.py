import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ExternalServiceError, NotFoundError, ValidationAppError
from app.models.address import Address
from app.repositories.address_repository import AddressRepository
from app.schemas.address import AddressCreate, AddressUpdate
from app.services import envia_client

_LOCATION_FIELDS = {"city", "state", "country", "postal_code"}


async def _check_place(values: dict[str, Any]) -> None:
    """A Colombian address must name a city Envia knows in its department
    (carriers need its DANE code), and gets that city's postal code, so the
    customer doesn't have to know it. If Envia's geocodes is down, a typed
    postal code is kept unchecked rather than blocking the customer."""
    if str(values.get("country") or "").upper() != "CO":
        if not values.get("postal_code"):
            raise ValidationAppError("postal_code is required outside Colombia.")
        return
    try:
        place = await envia_client.locate(values["state"], values["city"])
    except ExternalServiceError:
        if values.get("postal_code"):
            return
        raise
    if place is None:
        raise ValidationAppError(
            f"La ciudad '{values['city']}' no existe en el departamento '{values['state']}'."
        )
    values["postal_code"] = place.postal_code


class AddressService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = AddressRepository(db)

    async def create(self, user_id: uuid.UUID, data: AddressCreate) -> Address:
        values = data.model_dump()
        await _check_place(values)
        return await self.repo.create({**values, "user_id": user_id})

    async def list_for_user(self, user_id: uuid.UUID) -> list[Address]:
        return await self.repo.list_for_user(user_id)

    async def get_for_user(self, user_id: uuid.UUID, address_id: uuid.UUID) -> Address:
        address = await self.repo.get(address_id)
        if address is None or address.user_id != user_id:
            raise NotFoundError(f"Address {address_id} not found.")
        return address

    async def update(self, user_id: uuid.UUID, address_id: uuid.UUID, data: AddressUpdate) -> Address:
        address = await self.get_for_user(user_id, address_id)
        values = data.model_dump(exclude_unset=True)
        if _LOCATION_FIELDS & values.keys():
            merged = {f: getattr(address, f) for f in _LOCATION_FIELDS} | values
            await _check_place(merged)
            values["postal_code"] = merged["postal_code"]
        return await self.repo.update(address, values)

    async def delete(self, user_id: uuid.UUID, address_id: uuid.UUID) -> None:
        address = await self.get_for_user(user_id, address_id)
        await self.repo.delete(address)
