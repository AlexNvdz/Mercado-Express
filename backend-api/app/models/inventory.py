"""Inventory model: one stock record per product (single-warehouse model).

Extending to multi-warehouse later means adding a `warehouse_id` column and
relaxing the `product_id` uniqueness to `(product_id, warehouse_id)` -- kept
simple for now per the current scope.
"""

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDPKMixin
from app.models.product import Product


class Inventory(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "inventory"
    __table_args__ = (
        CheckConstraint("quantity_on_hand >= 0", name="ck_inventory_qty_on_hand_non_negative"),
        CheckConstraint("quantity_reserved >= 0", name="ck_inventory_qty_reserved_non_negative"),
        CheckConstraint(
            "quantity_reserved <= quantity_on_hand", name="ck_inventory_reserved_lte_on_hand"
        ),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    quantity_on_hand: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    quantity_reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    reorder_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    product: Mapped["Product"] = relationship(back_populates="inventory")

    @property
    def quantity_available(self) -> int:
        return self.quantity_on_hand - self.quantity_reserved
