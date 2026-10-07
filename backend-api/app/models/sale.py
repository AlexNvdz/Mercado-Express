"""Sale model: append-only financial ledger, kept separate from `Order`
(which tracks mutable lifecycle state) so reporting can query clean data.

Each order has at most two entries, never edited or deleted:
- one `sale` entry (amount >= 0), written once its payment completes;
- one `reversal` entry (amount <= 0, the negated sale amount), written if
  that paid order is later cancelled or refunded.

So `SUM(total_amount)` over the ledger is net revenue. The unique
(order_id, kind) constraint makes a double sale or double reversal
impossible at the database level.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import SaleKind

if TYPE_CHECKING:
    from app.models.order import Order


class Sale(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "sales"
    __table_args__ = (
        UniqueConstraint("order_id", "kind", name="uq_sales_order_kind"),
        CheckConstraint(
            "(kind = 'sale' AND total_amount >= 0) OR (kind = 'reversal' AND total_amount <= 0)",
            name="ck_sales_amount_sign_matches_kind",
        ),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[SaleKind] = mapped_column(
        Enum(
            SaleKind,
            name="sale_kind",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=SaleKind.SALE,
        server_default=SaleKind.SALE.value,
    )
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    # When the entry was recorded: the payment time for a `sale`, the
    # cancellation/refund time for a `reversal`.
    sold_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    order: Mapped["Order"] = relationship(back_populates="sales")
