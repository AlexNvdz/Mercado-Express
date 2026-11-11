"""Colombian departments (a fixed table, see envia_client.DEPARTMENTS) and
their cities from Envia.com's public geocodes (cached in memory): what the
address form offers. Public."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.exceptions import NotFoundError
from app.services import envia_client

router = APIRouter(prefix="/locations", tags=["locations"])


class StateOut(BaseModel):
    code: str
    name: str


@router.get("/co/states", response_model=list[StateOut])
async def list_states() -> list[StateOut]:
    return [StateOut(**s) for s in envia_client.states()]


@router.get("/co/states/{state}/cities", response_model=list[str])
async def list_cities(state: str) -> list[str]:
    """`state` is the department's code ("AN") or name ("Antioquia")."""
    code = envia_client.state_code(state)
    if code is None:
        raise NotFoundError(f"Department '{state}' not found.")
    return await envia_client.cities(code)
