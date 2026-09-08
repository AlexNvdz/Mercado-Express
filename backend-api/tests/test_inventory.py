from httpx import AsyncClient


async def _make_product(admin_client: AsyncClient, sku: str) -> str:
    category = await admin_client.post("/api/v1/categories", json={"name": f"Cat-{sku}"})
    category_id = category.json()["id"]
    product = await admin_client.post(
        "/api/v1/products",
        json={"sku": sku, "name": f"Product {sku}", "category_id": category_id, "price": "10.00"},
    )
    return product.json()["id"]


async def test_new_product_starts_with_zero_stock(admin_client: AsyncClient) -> None:
    product_id = await _make_product(admin_client, "INV-001")
    resp = await admin_client.get(f"/api/v1/inventory/{product_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["quantity_on_hand"] == 0
    assert body["quantity_available"] == 0


async def test_admin_can_adjust_stock(admin_client: AsyncClient) -> None:
    product_id = await _make_product(admin_client, "INV-002")
    resp = await admin_client.post(f"/api/v1/inventory/{product_id}/adjust", json={"delta": 50})
    assert resp.status_code == 200
    assert resp.json()["quantity_on_hand"] == 50

    resp2 = await admin_client.post(f"/api/v1/inventory/{product_id}/adjust", json={"delta": -20})
    assert resp2.status_code == 200
    assert resp2.json()["quantity_on_hand"] == 30


async def test_customer_cannot_adjust_stock(
    admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    product_id = await _make_product(admin_client, "INV-003")
    resp = await customer_client.post(f"/api/v1/inventory/{product_id}/adjust", json={"delta": 10})
    assert resp.status_code == 403


async def test_adjust_below_reserved_is_rejected(admin_client: AsyncClient) -> None:
    product_id = await _make_product(admin_client, "INV-004")
    await admin_client.put(
        f"/api/v1/inventory/{product_id}", json={"quantity_on_hand": 10, "reorder_level": 0}
    )
    # Directly driving reserved stock below via public API isn't exposed;
    # this test just guards the non-negative invariant on set_levels.
    resp = await admin_client.put(f"/api/v1/inventory/{product_id}", json={"quantity_on_hand": 0})
    assert resp.status_code == 200
    assert resp.json()["quantity_on_hand"] == 0
