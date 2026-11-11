"""Inbound webhooks from third parties: public (no JWT), each guarded by its
own shared secret."""

import hashlib
import hmac
import json
import logging
import secrets

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.exceptions import AppError, AuthenticationError, NotFoundError
from app.services.shipment_service import ShipmentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _envia_signature_ok(request: Request, body: bytes) -> bool:
    """Envia signs real deliveries `X-Webhook-Signature: v1=<hex>` with
    HMAC-SHA256(auth_token, "<X-Webhook-Timestamp>.<X-Webhook-Event>.<body>")
    (checked against the sandbox 2026-11-11). Unsigned requests (its test
    call) pass: only the URL token guards those."""
    signature = request.headers.get("X-Webhook-Signature")
    secret = settings.ENVIA_WEBHOOK_SECRET
    if not signature or not secret:
        return True
    timestamp = request.headers.get("X-Webhook-Timestamp", "")
    event = request.headers.get("X-Webhook-Event", "")
    message = f"{timestamp}.{event}.".encode() + body
    expected = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature.removeprefix("v1="), expected)


@router.post("/envia")
async def envia_tracking(
    request: Request,
    token: str = Query(description="ENVIA_WEBHOOK_TOKEN, part of the URL registered in Envia."),
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    """Envia's tracking webhook (type 3, `tracking.simple`): moves the
    shipment along like POST /shipments/{id}/sync, with no actor. Anything
    that isn't about one of our labels, or can't apply, still answers 200
    (`{"applied": false}`) so Envia stops retrying it. 401 on a wrong token
    or, with ENVIA_WEBHOOK_SECRET set, a wrong signature."""
    expected = settings.ENVIA_WEBHOOK_TOKEN
    if not expected:
        raise NotFoundError("Not Found")
    if not secrets.compare_digest(token.encode(), expected.encode()):
        raise AuthenticationError("Invalid webhook token.")
    body = await request.body()
    if not _envia_signature_ok(request, body):
        raise AuthenticationError("Invalid webhook signature.")
    try:
        payload = json.loads(body)
    except ValueError:
        return {"applied": False}
    try:
        shipment = await ShipmentService(db).handle_envia_webhook(payload)
    except AppError as exc:
        logger.warning("Envia webhook not applied: %s (payload %s)", exc.detail, payload)
        return {"applied": False}
    return {"applied": shipment is not None}
