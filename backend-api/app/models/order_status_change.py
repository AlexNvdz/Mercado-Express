"""Append-only history of order status changes (`order_status_history`).

One row per change: who (actor), from/to status, what triggered it
(source) and when. Rows are only ever inserted by the services that change
`Order.status`; nothing updates or deletes them. `created_at` uses
`clock_timestamp()` rather than `now()`, so rows written in the same
transaction still sort in insertion order.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, UUIDPKMixin
from app.models.enums import OrderStatus, OrderStatusChangeSource

if TYPE_CHECKING:
    from app.models.user import User


def _order_status_enum() -> Enum:
    # Same native type as orders.status (`order_status`), not a new one.
    return Enum(
        OrderStatus,
        name="order_status",
        native_enum=True,
        values_callable=lambda enum_cls: [member.value for member in enum_cls],
    )


class OrderStatusChange(UUIDPKMixin, Base):
    __tablename__ = "order_status_history"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # NULL only for the `order_created` entry.
    from_status: Mapped[OrderStatus | None] = mapped_column(_order_status_enum(), nullable=True)
    to_status: Mapped[OrderStatus] = mapped_column(_order_status_enum(), nullable=False)
    source: Mapped[OrderStatusChangeSource] = mapped_column(
        Enum(
            OrderStatusChangeSource,
            name="order_status_change_source",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp(), nullable=False
    )

    actor: Mapped["User | None"] = relationship()
