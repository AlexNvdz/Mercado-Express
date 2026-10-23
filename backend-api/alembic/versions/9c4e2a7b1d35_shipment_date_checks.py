"""shipment date checks

Revision ID: 9c4e2a7b1d35
Revises: 377398800f5e
Create Date: 2026-10-22 12:00:00.000000

Two named CHECK constraints on `shipments`:
- `ck_shipments_delivered_has_delivered_at`: a `delivered` shipment has
  `delivered_at`.
- `ck_shipments_in_transit_has_shipped_at`: an `in_transit` shipment has
  `shipped_at`.

ShipmentService already sets both dates on ship/deliver; this makes the
database reject any other writer (a script, a manual INSERT) that skips
them. Hand-written: autogenerate does not detect CHECK constraints.

Adding a CHECK validates the existing rows, so the upgrade fails (and
rolls back) if any shipment already breaks the rule.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9c4e2a7b1d35"
down_revision: str | Sequence[str] | None = "377398800f5e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_check_constraint(
        "ck_shipments_in_transit_has_shipped_at",
        "shipments",
        "status <> 'in_transit' OR shipped_at IS NOT NULL",
    )
    op.create_check_constraint(
        "ck_shipments_delivered_has_delivered_at",
        "shipments",
        "status <> 'delivered' OR delivered_at IS NOT NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_shipments_delivered_has_delivered_at", "shipments", type_="check")
    op.drop_constraint("ck_shipments_in_transit_has_shipped_at", "shipments", type_="check")
