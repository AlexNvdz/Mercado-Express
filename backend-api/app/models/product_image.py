"""Product image model: local-disk stored images per product.

Files live under `settings.MEDIA_ROOT/products/{product_id}/` (see
app/services/storage_service.py), served through the `/media` static mount
in app/main.py. Deleting a ProductImage row here does NOT remove the file
from disk -- files are only purged in bulk when the parent Product itself is
deleted (see ProductService.delete), per product requirements: image files
are only removed when the whole product goes away.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.base_class import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.product import Product


class ProductImage(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "product_images"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    product: Mapped["Product"] = relationship(back_populates="images")

    @property
    def url(self) -> str:
        """Absolute public URL for this image, served by the `/media`
        static mount. Absolute (not just MEDIA_URL + file_path) because the
        frontend is a different origin/port and loads this directly."""
        return f"{settings.PUBLIC_BASE_URL}{settings.MEDIA_URL}/{self.file_path}"
