from pathlib import Path

import pytest
from httpx import AsyncClient

from app.core.config import settings

pytestmark = pytest.mark.asyncio

_FAKE_JPEG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


async def _make_product(admin_client: AsyncClient, sku: str = "IMG-001") -> str:
    category = await admin_client.post("/api/v1/categories", json={"name": f"Cat-{sku}"})
    assert category.status_code == 201
    product = await admin_client.post(
        "/api/v1/products",
        json={
            "sku": sku,
            "name": "Widget",
            "category_id": category.json()["id"],
            "price": "9.99",
        },
    )
    assert product.status_code == 201
    return product.json()["id"]


async def test_admin_can_upload_image_and_see_it_on_the_product(admin_client: AsyncClient) -> None:
    product_id = await _make_product(admin_client, "IMG-001")

    resp = await admin_client.post(
        f"/api/v1/products/{product_id}/images",
        files={"file": ("photo.jpg", _FAKE_JPEG, "image/jpeg")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["position"] == 0
    assert body["url"].endswith(".jpg")
    assert Path(settings.MEDIA_ROOT, "products", product_id).exists()

    fetched = await admin_client.get(f"/api/v1/products/{product_id}")
    assert len(fetched.json()["images"]) == 1
    assert fetched.json()["images"][0]["url"] == body["url"]


async def test_customer_cannot_upload_product_image(
    admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    product_id = await _make_product(admin_client, "IMG-002")
    resp = await customer_client.post(
        f"/api/v1/products/{product_id}/images",
        files={"file": ("photo.jpg", _FAKE_JPEG, "image/jpeg")},
    )
    assert resp.status_code == 403


async def test_upload_rejects_unsupported_content_type(admin_client: AsyncClient) -> None:
    product_id = await _make_product(admin_client, "IMG-003")
    resp = await admin_client.post(
        f"/api/v1/products/{product_id}/images",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 422


async def test_upload_for_missing_product_returns_404(admin_client: AsyncClient) -> None:
    resp = await admin_client.post(
        "/api/v1/products/00000000-0000-0000-0000-000000000000/images",
        files={"file": ("photo.jpg", _FAKE_JPEG, "image/jpeg")},
    )
    assert resp.status_code == 404


async def test_deleting_one_image_detaches_it_but_leaves_the_file_on_disk(
    admin_client: AsyncClient,
) -> None:
    product_id = await _make_product(admin_client, "IMG-004")
    uploaded = await admin_client.post(
        f"/api/v1/products/{product_id}/images",
        files={"file": ("photo.jpg", _FAKE_JPEG, "image/jpeg")},
    )
    image_id = uploaded.json()["id"]
    file_on_disk = Path(settings.MEDIA_ROOT, "products", product_id)
    assert any(file_on_disk.iterdir())

    resp = await admin_client.delete(f"/api/v1/products/{product_id}/images/{image_id}")
    assert resp.status_code == 204

    fetched = await admin_client.get(f"/api/v1/products/{product_id}")
    assert fetched.json()["images"] == []
    # Removing the row never touches disk -- only a full product delete does.
    assert any(file_on_disk.iterdir())


async def test_deleting_the_product_purges_its_image_files(admin_client: AsyncClient) -> None:
    product_id = await _make_product(admin_client, "IMG-005")
    await admin_client.post(
        f"/api/v1/products/{product_id}/images",
        files={"file": ("photo.jpg", _FAKE_JPEG, "image/jpeg")},
    )
    product_dir = Path(settings.MEDIA_ROOT, "products", product_id)
    assert product_dir.exists()

    resp = await admin_client.delete(f"/api/v1/products/{product_id}")
    assert resp.status_code == 204
    assert not product_dir.exists()
