"""Append-only history of manual stock changes (`inventory_history`).

One row per staff adjustment (`adjust`, a signed delta) or level set
(`set_levels`, absolute values): who, the reason, and the on-hand and
reorder-level values before and after. Reservations, releases and
fulfillments driven by orders are not recorded here -- they follow from the
order's own status history. Rows are only ever inserted; `created_at` uses
`clock_timestamp()` so rows from one transaction keep their order.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, UUIDPKMixin
from app.models.enums import InventoryChangeKind

if TYPE_CHECKING:
    from app.models.user import User


class InventoryChange(UUIDPKMixin, Base):
    __tablename__ = "inventory_history"
    # Serves the per-product, newest-first paginated read.
    __table_args__ = (Index("ix_inventory_history_product_id_created_at", "product_id", "created_at"),)

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[InventoryChangeKind] = mapped_column(
        Enum(
            InventoryChangeKind,
            name="inventory_change_kind",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    quantity_on_hand_before: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_on_hand_after: Mapped[int] = mapped_column(Integer, nullable=False)
    reorder_level_before: Mapped[int] = mapped_column(Integer, nullable=False)
    reorder_level_after: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp(), nullable=False
    )

    actor: Mapped["User | None"] = relationship()

    @property
    def quantity_delta(self) -> int:
        return self.quantity_on_hand_after - self.quantity_on_hand_before
