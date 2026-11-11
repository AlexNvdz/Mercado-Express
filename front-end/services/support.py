"""
Support claims (refunds). See ../API_CONTRACT.md#apiv1soporte.

    POST /api/v1/soporte/procesar-reclamo   {"mensaje": "..."}
        -> {decision: aprobado|rechazado|revision_manual, motivo, order_id, order_status}

The backend decides everything: a local LLM only reads the text, fixed rules
refund a `delivered` order of the caller at most 30 days after delivery.
Nothing is stored for `revision_manual`, so no one reviews it afterwards.
"""

from __future__ import annotations

import re

from django.conf import settings

from . import mock_data
from .api_client import ApiClient

# The backend waits up to 60 s for the LLM (OLLAMA_TIMEOUT_SECONDS); the
# shared client's 5 s would cut every claim short.
CLAIM_TIMEOUT_SECONDS = 65
_claims_client = ApiClient(timeout=CLAIM_TIMEOUT_SECONDS)

_REFUND_WORDS = re.compile(r"reembols|devu[eé]lv|plata|dinero", re.IGNORECASE)


def build_message(order_id: str, mensaje: str) -> str:
    """Customers never see order UUIDs, but the backend only acts on one
    written literally in the text: the chosen order goes in front."""
    return f"Pedido {order_id}: {mensaje}"


def procesar_reclamo(token: str, order_id: str, mensaje: str) -> dict:
    texto = build_message(order_id, mensaje)
    if settings.API_USE_MOCKS:
        return _mock_procesar_reclamo(order_id, texto)
    return _claims_client.post("/api/v1/soporte/procesar-reclamo", token=token, json={"mensaje": texto})


def _mock_procesar_reclamo(order_id: str, texto: str) -> dict:
    """Rough stand-in for the LLM plus the backend rules, for tests and UI work."""
    order = next((o for o in mock_data.MOCK_ORDERS if o["id"] == order_id), None)
    if order is None:
        return {"decision": "rechazado", "motivo": "Pedido no encontrado.", "order_id": None, "order_status": None}
    if not _REFUND_WORDS.search(texto):
        return {
            "decision": "revision_manual",
            "motivo": "Solo los reembolsos se procesan automáticamente.",
            "order_id": order_id,
            "order_status": order["status"],
        }
    if order["status"] != "delivered":
        return {
            "decision": "rechazado",
            "motivo": f"Solo se reembolsan pedidos entregados (estado: '{order['status']}').",
            "order_id": order_id,
            "order_status": order["status"],
        }
    order["status"] = "refunded"
    return {"decision": "aprobado", "motivo": "Reembolso aprobado.", "order_id": order_id, "order_status": "refunded"}
