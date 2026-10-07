"""Shared enums backing PostgreSQL native ENUM columns.

Kept as plain `str` enums so they serialize cleanly through Pydantic and the
JSON API without extra config.
"""

from enum import StrEnum


class UserRole(StrEnum):
    CUSTOMER = "customer"
    EMPLOYEE = "employee"
    ADMIN = "admin"


class OrderStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    PREPARING = "preparing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class ShipmentStatus(StrEnum):
    PENDING = "pending"
    PREPARING = "preparing"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETURNED = "returned"
    # Set when the order is cancelled/refunded before the shipment was
    # dispatched (see OrderService.transition_status).
    CANCELLED = "cancelled"


class OrderStatusChangeSource(StrEnum):
    """What triggered an order status change (`order_status_history.source`)."""

    ORDER_CREATED = "order_created"  # POST /orders (initial `pending`)
    PAYMENT = "payment"  # completed POST /payments
    MANUAL = "manual"  # staff PATCH /orders/{id}/status
    CUSTOMER_CANCEL = "customer_cancel"  # POST /orders/{id}/cancel
    SHIPMENT_CREATED = "shipment_created"  # POST /shipments/order/{id}
    SHIPMENT_DISPATCHED = "shipment_dispatched"  # POST /shipments/{id}/ship
    SHIPMENT_DELIVERED = "shipment_delivered"  # POST /shipments/{id}/deliver


class InventoryChangeKind(StrEnum):
    """Manual staff change recorded in `inventory_history`."""

    ADJUST = "adjust"  # POST /inventory/{product_id}/adjust (signed delta)
    SET_LEVELS = "set_levels"  # PUT /inventory/{product_id} (absolute values)


class SaleKind(StrEnum):
    """Kind of entry in the append-only `sales` ledger: `sale` is written
    when a payment completes (positive amount); `reversal` is written when
    that paid order is later cancelled or refunded (negative amount)."""

    SALE = "sale"
    REVERSAL = "reversal"
