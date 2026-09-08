"""ORM models. Import all here so Alembic autogenerate (via app/db/base.py)
sees every mapped class."""

from app.models.address import Address
from app.models.category import Category
from app.models.inventory import Inventory
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.payment import Payment
from app.models.product import Product
from app.models.sale import Sale
from app.models.shipment import Shipment
from app.models.user import User

__all__ = [
    "Address",
    "Category",
    "Inventory",
    "Order",
    "OrderItem",
    "Payment",
    "Product",
    "Sale",
    "Shipment",
    "User",
]
