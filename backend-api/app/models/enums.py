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


class SaleKind(StrEnum):
    """Kind of entry in the append-only `sales` ledger: `sale` is written
    when a payment completes (positive amount); `reversal` is written when
    that paid order is later cancelled or refunded (negative amount)."""

    SALE = "sale"
    REVERSAL = "reversal"
