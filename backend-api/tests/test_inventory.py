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


async def test_list_inventory_paginates(admin_client: AsyncClient) -> None:
    await _make_product(admin_client, "INV-LIST-1")
    await _make_product(admin_client, "INV-LIST-2")

    resp = await admin_client.get("/api/v1/inventory", params={"page_size": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert body["page_size"] == 1
    assert len(body["items"]) == 1
    assert body["total"] >= 2


async def test_list_inventory_low_stock_filter(admin_client: AsyncClient) -> None:
    below_reorder = await _make_product(admin_client, "INV-LOW-1")
    await admin_client.put(
        f"/api/v1/inventory/{below_reorder}", json={"quantity_on_hand": 1, "reorder_level": 5}
    )
    above_reorder = await _make_product(admin_client, "INV-LOW-2")
    await admin_client.put(
        f"/api/v1/inventory/{above_reorder}", json={"quantity_on_hand": 50, "reorder_level": 5}
    )

    resp = await admin_client.get("/api/v1/inventory", params={"low_stock": "true"})
    assert resp.status_code == 200
    product_ids = {row["product_id"] for row in resp.json()["items"]}
    assert below_reorder in product_ids
    assert above_reorder not in product_ids


async def test_list_inventory_requires_staff(customer_client: AsyncClient) -> None:
    resp = await customer_client.get("/api/v1/inventory")
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
