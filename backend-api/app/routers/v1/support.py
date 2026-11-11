"""Support claims: LLM parses the text, OrderService applies the rules."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.support import DecisionReclamo, ReclamoClienteInput, ReclamoResultadoOut
from app.services.ai_service import extraer_intencion
from app.services.order_service import OrderService

router = APIRouter(prefix="/soporte", tags=["soporte"])


@router.post("/procesar-reclamo", response_model=ReclamoResultadoOut)
async def procesar_reclamo(
    data: ReclamoClienteInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReclamoResultadoOut:
    """Always 200: approved, rejected or sent to manual review, with the reason.
    Only the caller's own orders; someone else's reads as not found."""
    intencion = await extraer_intencion(data.mensaje)
    if intencion is None:
        return ReclamoResultadoOut(
            decision=DecisionReclamo.REVISION_MANUAL, motivo="No se pudo interpretar el reclamo."
        )
    # Anti-hallucination: the UUID must be literally in the customer's text.
    # shortcut: a UUID written without hyphens goes to manual review; normalize it here if that shows up.
    if intencion.order_uuid is not None and str(intencion.order_uuid) not in data.mensaje.lower():
        return ReclamoResultadoOut(
            decision=DecisionReclamo.REVISION_MANUAL,
            motivo="El número de pedido extraído no aparece en el mensaje.",
        )
    return await OrderService(db).procesar_reclamo(intencion, customer_id=current_user.id)
