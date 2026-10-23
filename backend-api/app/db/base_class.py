"""Declarative base and shared mixins for all ORM models."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class UUIDPKMixin:
    """Adds a UUID primary key column named `id`."""

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    """Adds `created_at` / `updated_at` timestamp columns (UTC, server-set)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


def trigram_index(table: str, column: str) -> Index:
    """GIN pg_trgm index, so the `search` filters (`column ILIKE '%text%'`,
    which a btree can't serve) use an index. Needs the pg_trgm extension:
    created by migration 5d8e1f2a9b47 and by the tests' conftest."""
    return Index(
        f"ix_{table}_{column}_trgm", column, postgresql_using="gin", postgresql_ops={column: "gin_trgm_ops"}
    )
