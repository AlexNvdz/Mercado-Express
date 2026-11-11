"""add support_claim to order_status_change_source

Revision ID: e7a3c91f5b20
Revises: 5d8e1f2a9b47
Create Date: 2026-11-10 10:00:00.000000

Adds `support_claim` to the native enum `order_status_change_source`: the
history entry of a `delivered -> refunded` change approved by
POST /soporte/procesar-reclamo (OrderService.procesar_reclamo).

Hand-written: autogenerate does not detect enum value changes. Same
rename/recreate pattern as 4b9647ef29f0, needed anyway for the downgrade
(Postgres can't drop an enum value).

Downgrade: those entries become `manual`, the closest old value. Their
orders stay `refunded`.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7a3c91f5b20"
down_revision: str | Sequence[str] | None = "5d8e1f2a9b47"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_VALUES = (
    "order_created",
    "payment",
    "manual",
    "customer_cancel",
    "shipment_created",
    "shipment_dispatched",
    "shipment_delivered",
)
_NEW_VALUES = (*_OLD_VALUES, "support_claim")


def _swap_type(values: tuple[str, ...], old_type_name: str) -> None:
    """Recreates `order_status_change_source` with `values` and moves the column to it."""
    op.execute(f"ALTER TYPE order_status_change_source RENAME TO {old_type_name}")
    sa.Enum(*values, name="order_status_change_source").create(op.get_bind())
    op.execute(
        "ALTER TABLE order_status_history ALTER COLUMN source TYPE order_status_change_source "
        "USING source::text::order_status_change_source"
    )
    op.execute(f"DROP TYPE {old_type_name}")


def upgrade() -> None:
    """Upgrade schema."""
    _swap_type(_NEW_VALUES, "order_status_change_source_old")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("UPDATE order_status_history SET source = 'manual' WHERE source = 'support_claim'")
    _swap_type(_OLD_VALUES, "order_status_change_source_new")
