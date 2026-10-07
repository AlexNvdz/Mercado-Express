import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _make_category(admin_client: AsyncClient, name: str = "Electronics") -> str:
    resp = await admin_client.post("/api/v1/categories", json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_admin_can_create_category_and_product(admin_client: AsyncClient) -> None:
    category_id = await _make_category(admin_client)

    resp = await admin_client.post(
        "/api/v1/products",
        json={"sku": "SKU-001", "name": "Widget", "category_id": category_id, "price": "19.99"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["sku"] == "SKU-001"
    assert body["price"] == "19.99"


async def test_customer_cannot_create_product(
    customer_client: AsyncClient, admin_client: AsyncClient
) -> None:
    category_id = await _make_category(admin_client, "Books")
    resp = await customer_client.post(
        "/api/v1/products",
        json={"sku": "SKU-002", "name": "Novel", "category_id": category_id, "price": "9.99"},
    )
    assert resp.status_code == 403


async def test_duplicate_sku_conflicts(admin_client: AsyncClient) -> None:
    category_id = await _make_category(admin_client, "Toys")
    payload = {"sku": "SKU-DUPE", "name": "Toy", "category_id": category_id, "price": "5.00"}
    first = await admin_client.post("/api/v1/products", json=payload)
    assert first.status_code == 201
    second = await admin_client.post("/api/v1/products", json=payload)
    assert second.status_code == 409


async def test_creating_product_for_missing_category_returns_404(admin_client: AsyncClient) -> None:
    resp = await admin_client.post(
        "/api/v1/products",
        json={
            "sku": "SKU-003",
            "name": "Ghost",
            "category_id": "00000000-0000-0000-0000-000000000000",
            "price": "1.00",
        },
    )
    assert resp.status_code == 404


async def test_list_and_get_product(admin_client: AsyncClient) -> None:
    category_id = await _make_category(admin_client, "Garden")
    created = await admin_client.post(
        "/api/v1/products",
        json={"sku": "SKU-004", "name": "Shovel", "category_id": category_id, "price": "15.00"},
    )
    product_id = created.json()["id"]

    listed = await admin_client.get("/api/v1/products")
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    fetched = await admin_client.get(f"/api/v1/products/{product_id}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Shovel"


async def test_get_missing_product_returns_404(admin_client: AsyncClient) -> None:
    resp = await admin_client.get("/api/v1/products/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


async def test_search_matches_name_or_sku_case_insensitively(admin_client: AsyncClient) -> None:
    category_id = await _make_category(admin_client, "Search Cat")
    await admin_client.post(
        "/api/v1/products",
        json={"sku": "SRCH-001", "name": "Wireless Mouse", "category_id": category_id, "price": "9.99"},
    )
    await admin_client.post(
        "/api/v1/products",
        json={"sku": "SRCH-002", "name": "Keyboard", "category_id": category_id, "price": "29.99"},
    )

    by_name = await admin_client.get("/api/v1/products", params={"search": "mouse"})
    assert by_name.status_code == 200
    names = [p["name"] for p in by_name.json()["items"]]
    assert "Wireless Mouse" in names
    assert "Keyboard" not in names

    by_sku = await admin_client.get("/api/v1/products", params={"search": "srch-002"})
    assert by_sku.status_code == 200
    skus = [p["sku"] for p in by_sku.json()["items"]]
    assert "SRCH-002" in skus
    assert "SRCH-001" not in skus


async def test_inactive_products_are_listed_only_for_staff_on_request(
    client: AsyncClient, admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    category_id = await _make_category(admin_client, "Inactive Cat")

    async def create(sku: str, *, active: bool) -> str:
        resp = await admin_client.post(
            "/api/v1/products",
            json={"sku": sku, "name": sku, "category_id": category_id, "price": "3.00", "is_active": active},
        )
        assert resp.status_code == 201
        return resp.json()["id"]

    await create("ACT-1", active=True)
    inactive_id = await create("INACT-1", active=False)

    async def skus(c: AsyncClient, **params: str) -> set[str]:
        resp = await c.get("/api/v1/products", params=params)
        assert resp.status_code == 200
        return {p["sku"] for p in resp.json()["items"]}

    # Default: active only, for everyone (staff included).
    assert await skus(client) == {"ACT-1"}
    assert await skus(admin_client) == {"ACT-1"}
    assert await skus(admin_client, include_inactive="true") == {"ACT-1", "INACT-1"}

    # The option is staff-only: rejected, not silently ignored.
    anonymous = await client.get("/api/v1/products", params={"include_inactive": "true"})
    assert anonymous.status_code == 401
    customer = await customer_client.get("/api/v1/products", params={"include_inactive": "true"})
    assert customer.status_code == 403

    # Detail by id stays public for inactive products; ordering one is refused.
    detail = await client.get(f"/api/v1/products/{inactive_id}")
    assert detail.status_code == 200
    assert detail.json()["is_active"] is False
    order = await customer_client.post(
        "/api/v1/orders", json={"items": [{"product_id": inactive_id, "quantity": 1}]}
    )
    assert order.status_code == 404
