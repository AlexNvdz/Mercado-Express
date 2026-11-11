"""Support claims (POST /soporte/procesar-reclamo): the customer's free text,
the intent the LLM extracts from it, and the deterministic decision."""

import uuid
from enum import StrEnum

from pydantic import BaseModel, Field

from app.models.enums import OrderStatus


class AccionSolicitada(StrEnum):
    REEMBOLSO = "reembolso"
    CANCELACION = "cancelacion"
    ESTADO_PEDIDO = "estado_pedido"
    OTRO = "otro"


class DecisionReclamo(StrEnum):
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"
    REVISION_MANUAL = "revision_manual"


class ReclamoClienteInput(BaseModel):
    mensaje: str = Field(..., min_length=10, max_length=2000, description="Texto libre del cliente.")


class IntencionIAOutput(BaseModel):
    """What the LLM must return. It is only a parse of the text: every rule
    is checked afterwards by OrderService.procesar_reclamo."""

    accion_solicitada: AccionSolicitada
    order_uuid: uuid.UUID | None = Field(
        default=None, description="UUID del pedido tal como aparece en el texto; null si no hay."
    )
    nivel_confianza: float = Field(..., ge=0, le=1)


class ReclamoResultadoOut(BaseModel):
    decision: DecisionReclamo
    motivo: str
    order_id: uuid.UUID | None = None
    order_status: OrderStatus | None = None
