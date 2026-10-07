"""add cancelled to shipment_status

Revision ID: 4b9647ef29f0
Revises: bdd517b5e052
Create Date: 2026-10-06 22:01:37.027749

Adds `cancelled` to the native enum `shipment_status`. An undispatched
shipment moves to `cancelled` when its order is cancelled or refunded, so
it can no longer be shipped (see OrderService.transition_status).

Hand-written: autogenerate does not detect enum value changes. Same
rename/recreate pattern as 6bf0432e1cd9. `ALTER TYPE ... ADD VALUE` is not
used because a value added that way cannot be used in the same
transaction, and the backfill below needs it.

Backfill: shipments that were never dispatched (`pending`/`preparing`) but
belong to an order that is already cancelled or refunded become
`cancelled`.

Downgrade: the old type has no `cancelled`, so those rows become `failed`,
the closest old value that the old code also refuses to ship.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4b9647ef29f0"
down_revision: str | Sequence[str] | None = "bdd517b5e052"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_VALUES = ("pending", "preparing", "in_transit", "delivered", "failed", "returned")
_NEW_VALUES = (*_OLD_VALUES, "cancelled")


def _swap_type(values: tuple[str, ...], old_type_name: str) -> None:
    """Recreates `shipment_status` with `values` and moves the column to it."""
    op.execute(f"ALTER TYPE shipment_status RENAME TO {old_type_name}")
    sa.Enum(*values, name="shipment_status").create(op.get_bind())
    op.execute("ALTER TABLE shipments ALTER COLUMN status DROP DEFAULT")
    op.execute(
        "ALTER TABLE shipments ALTER COLUMN status TYPE shipment_status USING status::text::shipment_status"
    )
    op.execute("ALTER TABLE shipments ALTER COLUMN status SET DEFAULT 'pending'")
    op.execute(f"DROP TYPE {old_type_name}")


def upgrade() -> None:
    """Upgrade schema."""
    _swap_type(_NEW_VALUES, "shipment_status_old")
    op.execute(
        "UPDATE shipments SET status = 'cancelled' FROM orders "
        "WHERE shipments.order_id = orders.id "
        "AND orders.status IN ('cancelled', 'refunded') "
        "AND shipments.status IN ('pending', 'preparing')"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("UPDATE shipments SET status = 'failed' WHERE status = 'cancelled'")
    _swap_type(_OLD_VALUES, "shipment_status_new")
