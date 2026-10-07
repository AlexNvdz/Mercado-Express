"""sale kind and reversal entries

Revision ID: bdd517b5e052
Revises: 1b502c1e4011
Create Date: 2026-10-06 22:00:52.527481

Turns `sales` into an append-only ledger that can record reversals: when a
paid order is cancelled or refunded, a second entry with a negative amount
is added, instead of editing or deleting the original sale.

- New native enum `sale_kind` (`sale`, `reversal`) and column `sales.kind`.
  Existing rows become `sale` through the server default.
- One entry per (order_id, kind) instead of one per order_id: the unique
  constraint `uq_sales_order_kind` replaces the unique index
  `ix_sales_order_id`. Its leading column still serves lookups by order_id.
- The sign check follows the kind: `ck_sales_amount_sign_matches_kind`
  replaces `ck_sales_total_non_negative`. Autogenerate does not compare
  CHECK constraints, so this part is hand-written.

Each rule stays enforced at every step: the new unique constraint and the
new check are created before the old ones are dropped.

Backfill: orders that were paid and then cancelled or refunded before this
migration get their reversal entry now, so net revenue is right for
existing data too. Its `sold_at` is the order's `updated_at`, the closest
record of when it was cancelled/refunded (terminal orders are not updated
afterwards).

Downgrade is lossy: the old schema cannot hold reversal entries (one row
per order, amount >= 0), so all of them are deleted first, backfilled or
not.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bdd517b5e052"
down_revision: str | Sequence[str] | None = "1b502c1e4011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SALE_KIND_VALUES = ("sale", "reversal")
_SIGN_MATCHES_KIND = "(kind = 'sale' AND total_amount >= 0) OR (kind = 'reversal' AND total_amount <= 0)"


def upgrade() -> None:
    """Upgrade schema."""
    postgresql.ENUM(*_SALE_KIND_VALUES, name="sale_kind").create(op.get_bind())
    op.add_column(
        "sales",
        sa.Column(
            "kind",
            postgresql.ENUM(*_SALE_KIND_VALUES, name="sale_kind", create_type=False),
            server_default="sale",
            nullable=False,
        ),
    )
    op.create_unique_constraint("uq_sales_order_kind", "sales", ["order_id", "kind"])
    op.drop_index("ix_sales_order_id", table_name="sales")
    op.create_check_constraint("ck_sales_amount_sign_matches_kind", "sales", _SIGN_MATCHES_KIND)
    op.drop_constraint("ck_sales_total_non_negative", "sales", type_="check")
    op.execute(
        "INSERT INTO sales (id, order_id, kind, total_amount, sold_at) "
        "SELECT gen_random_uuid(), s.order_id, 'reversal', -s.total_amount, o.updated_at "
        "FROM sales s JOIN orders o ON o.id = s.order_id "
        "WHERE s.kind = 'sale' AND o.status IN ('cancelled', 'refunded')"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DELETE FROM sales WHERE kind = 'reversal'")
    op.create_check_constraint("ck_sales_total_non_negative", "sales", "total_amount >= 0")
    op.drop_constraint("ck_sales_amount_sign_matches_kind", "sales", type_="check")
    op.create_index("ix_sales_order_id", "sales", ["order_id"], unique=True)
    op.drop_constraint("uq_sales_order_kind", "sales", type_="unique")
    op.drop_column("sales", "kind")
    postgresql.ENUM(name="sale_kind").drop(op.get_bind())
