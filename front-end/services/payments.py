"""
Payments. See ../API_CONTRACT.md#apiv1payments.

    POST /api/v1/payments                    {order_id, method, provider}
    GET  /api/v1/payments/{payment_id}
    GET  /api/v1/payments/order/{order_id}

No real payment gateway is integrated on the backend yet: POST completes the
payment immediately via a manual/placeholder gateway, moving the order to
`paid`. This module does not simulate a payment form or hold card data -- it
only forwards the checkout choice (payment method) to the backend.
"""

from __future__ import annotations

from django.conf import settings

from . import mock_data
from .api_client import api_client


def create_payment(token: str, order_id: str, method: str = "card", provider: str | None = None) -> dict:
    if settings.API_USE_MOCKS:
        order = next((o for o in mock_data.MOCK_ORDERS if o["id"] == str(order_id)), None)
        if order is not None:
            order["status"] = "paid"
        payment = {
            "id": "mock-payment",
            "order_id": order_id,
            "amount": order["total_amount"] if order else "0.00",
            "currency": "USD",
            "status": "completed",
            "provider": "manual",
            "method": method,
        }
        mock_data.MOCK_PAYMENTS.setdefault(str(order_id), []).append(payment)
        return payment
    return api_client.post(
        "/api/v1/payments", token=token, json={"order_id": order_id, "method": method, "provider": provider}
    )


def list_payments_for_order(token: str, order_id: str) -> list[dict]:
    if settings.API_USE_MOCKS:
        return mock_data.MOCK_PAYMENTS.get(str(order_id), [])
    return api_client.get(f"/api/v1/payments/order/{order_id}", token=token)
