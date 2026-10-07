"""Product image storage, abstracted behind `ImageStorage` so a remote
backend (S3, etc.) can be plugged in later without touching the service or
router. No remote backend configured yet -- `LocalDiskImageStorage` writes
under `settings.MEDIA_ROOT` and is served back out via the `/media` static
mount in app/main.py."""

import abc
import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.exceptions import ValidationAppError

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB

_EXT_BY_CONTENT_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


class ImageStorage(abc.ABC):
    """Port for product image storage."""

    @abc.abstractmethod
    async def save(self, product_id: uuid.UUID, upload: UploadFile) -> str:
        """Validate and persist `upload` for `product_id`. Returns the value
        to store on ProductImage.file_path."""

    @abc.abstractmethod
    def delete_product_files(self, product_id: uuid.UUID) -> None:
        """Remove every file stored for `product_id`. Called only when the
        whole product is deleted (see ProductService.delete) -- removing a
        single ProductImage row never touches disk, by design."""


class LocalDiskImageStorage(ImageStorage):
    """No remote backend configured yet: writes under
    `settings.MEDIA_ROOT/products/{product_id}/`. Swap for e.g. an
    S3-backed ImageStorage later -- the rest of the system is unaffected."""

    def _product_dir(self, product_id: uuid.UUID) -> Path:
        return Path(settings.MEDIA_ROOT) / "products" / str(product_id)

    async def save(self, product_id: uuid.UUID, upload: UploadFile) -> str:
        if upload.content_type not in ALLOWED_CONTENT_TYPES:
            raise ValidationAppError(f"Unsupported image type '{upload.content_type}'.")

        data = await upload.read()
        if not data:
            raise ValidationAppError("Uploaded file is empty.")
        if len(data) > MAX_IMAGE_SIZE:
            raise ValidationAppError("Image exceeds the 5 MB size limit.")

        directory = self._product_dir(product_id)
        directory.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid.uuid4()}{_EXT_BY_CONTENT_TYPE[upload.content_type]}"
        (directory / filename).write_bytes(data)
        return f"products/{product_id}/{filename}"

    def delete_product_files(self, product_id: uuid.UUID) -> None:
        shutil.rmtree(self._product_dir(product_id), ignore_errors=True)
