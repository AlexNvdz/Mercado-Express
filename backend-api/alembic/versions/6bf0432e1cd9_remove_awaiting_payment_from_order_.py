"""remove awaiting_payment from order_status enum

Revision ID: 6bf0432e1cd9
Revises: de281d0b1fda
Create Date: 2026-09-12 14:48:22.525822

Simplifies the order lifecycle down to the 7 statuses the frontend actually
shows/manages: pending, paid, preparing, shipped, delivered, cancelled,
refunded. `awaiting_payment` was only ever reached (a) by a manual staff
override or (b) when a payment failed -- and in practice payments complete
synchronously via the manual gateway, so it added a state customers never
meaningfully saw or could act on. Failed payments now leave the order
`pending` (still retryable) instead of moving it to `awaiting_payment`.

Postgres enums can't drop a value in place, so this recreates the type:
existing `awaiting_payment` rows are folded into `pending` first (the same
status the frontend's order tracker already displayed them as), matching
how a customer never saw a difference between the two.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6bf0432e1cd9"
down_revision: str | Sequence[str] | None = "de281d0b1fda"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW_VALUES = ("pending", "paid", "preparing", "shipped", "delivered", "cancelled", "refunded")
_OLD_VALUES = (
    "pending",
    "awaiting_payment",
    "paid",
    "preparing",
    "shipped",
    "delivered",
    "cancelled",
    "refunded",
)


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("UPDATE orders SET status = 'pending' WHERE status = 'awaiting_payment'")
    op.execute("ALTER TYPE order_status RENAME TO order_status_old")
    new_enum = sa.Enum(*_NEW_VALUES, name="order_status")
    new_enum.create(op.get_bind())
    op.execute("ALTER TABLE orders ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE orders ALTER COLUMN status TYPE order_status USING status::text::order_status")
    op.execute("ALTER TABLE orders ALTER COLUMN status SET DEFAULT 'pending'")
    op.execute("DROP TYPE order_status_old")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TYPE order_status RENAME TO order_status_new")
    old_enum = sa.Enum(*_OLD_VALUES, name="order_status")
    old_enum.create(op.get_bind())
    op.execute("ALTER TABLE orders ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE orders ALTER COLUMN status TYPE order_status USING status::text::order_status")
    op.execute("ALTER TABLE orders ALTER COLUMN status SET DEFAULT 'pending'")
    op.execute("DROP TYPE order_status_new")
