"""Sale model: immutable financial record created once an order is paid.

Kept separate from `Order` (which tracks mutable lifecycle state) so
analytics/reporting can query a clean, append-only ledger.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.order import Order


class Sale(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "sales"
    __table_args__ = (CheckConstraint("total_amount >= 0", name="ck_sales_total_non_negative"),)

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    sold_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    order: Mapped["Order"] = relationship(back_populates="sale")
