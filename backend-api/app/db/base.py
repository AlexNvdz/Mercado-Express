"""Single import point for Alembic autogenerate: brings in Base.metadata with
every model registered via app.models."""

from app.db.base_class import Base
from app.models import (  # noqa: F401
    Address,
    Category,
    Inventory,
    InventoryChange,
    Order,
    OrderItem,
    OrderStatusChange,
    Payment,
    Product,
    Sale,
    Shipment,
    User,
)

__all__ = ["Base"]
