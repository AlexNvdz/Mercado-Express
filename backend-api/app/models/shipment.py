"""Shipment model. Provider-agnostic (`carrier` is free text); the
`service`/`label_url`/`tracking_url`/`shipping_cost` columns are filled only
when the label was bought through Envia.com (ShipmentService)."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import ShipmentStatus

if TYPE_CHECKING:
    from app.models.address import Address
    from app.models.order import Order


class Shipment(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "shipments"
    # A shipment that left (or arrived) must say when: ShipmentService sets
    # these on ship/deliver; the database enforces it for every other writer.
    __table_args__ = (
        CheckConstraint(
            "status <> 'in_transit' OR shipped_at IS NOT NULL",
            name="ck_shipments_in_transit_has_shipped_at",
        ),
        CheckConstraint(
            "status <> 'delivered' OR delivered_at IS NOT NULL",
            name="ck_shipments_delivered_has_delivered_at",
        ),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    address_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("addresses.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[ShipmentStatus] = mapped_column(
        Enum(
            ShipmentStatus,
            name="shipment_status",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=ShipmentStatus.PENDING,
        server_default=ShipmentStatus.PENDING.value,
        index=True,
    )
    carrier: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tracking_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    service: Mapped[str | None] = mapped_column(String(100), nullable=True)
    label_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tracking_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # What Envia charged the store for the label (the customer pays the flat fee).
    shipping_cost: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    order: Mapped["Order"] = relationship(back_populates="shipment")
    address: Mapped["Address"] = relationship()
