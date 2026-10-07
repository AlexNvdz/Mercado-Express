"""unique indexes instead of uq constraints

Revision ID: 1b502c1e4011
Revises: 6bf0432e1cd9
Create Date: 2026-10-06 21:02:46.136282

The hand-authored initial migration (2a6e6f24d115) gave each of these
columns a `uq_<table>_<column>` UNIQUE constraint plus a separate, plain
`ix_<table>_<column>` index. The models declare `unique=True, index=True`,
which SQLAlchemy renders as a single unique `ix_*` index -- so
`alembic check` kept reporting drift. This makes the database match the
models: the `ix_*` index becomes unique and the redundant `uq_*`
constraint goes away.

Each column keeps a uniqueness guarantee at every step: the unique `ix_*`
index is built while `uq_*` still exists, and `uq_*` is dropped only
after. (The whole upgrade also runs in one transaction -- Postgres DDL is
transactional.)
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1b502c1e4011"
down_revision: str | Sequence[str] | None = "6bf0432e1cd9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UNIQUE_COLUMNS = (
    ("categories", "name"),
    ("inventory", "product_id"),
    ("orders", "order_number"),
    ("products", "sku"),
    ("sales", "order_id"),
    ("shipments", "order_id"),
    ("users", "email"),
)


def upgrade() -> None:
    """Upgrade schema."""
    for table, column in _UNIQUE_COLUMNS:
        op.drop_index(f"ix_{table}_{column}", table_name=table)
        op.create_index(f"ix_{table}_{column}", table, [column], unique=True)
        op.drop_constraint(f"uq_{table}_{column}", table, type_="unique")


def downgrade() -> None:
    """Downgrade schema."""
    for table, column in _UNIQUE_COLUMNS:
        op.create_unique_constraint(f"uq_{table}_{column}", table, [column])
        op.drop_index(f"ix_{table}_{column}", table_name=table)
        op.create_index(f"ix_{table}_{column}", table, [column], unique=False)
