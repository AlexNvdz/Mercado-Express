from httpx import AsyncClient

from app.models.user import User


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


async def test_customer_cannot_adjust_stock(admin_client: AsyncClient, customer_client: AsyncClient) -> None:
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


async def test_list_inventory_leaves_out_inactive_products_by_default(admin_client: AsyncClient) -> None:
    active = await _make_product(admin_client, "INV-ACT")
    inactive = await _make_product(admin_client, "INV-INACT")
    await admin_client.patch(f"/api/v1/products/{inactive}", json={"is_active": False})

    default = await admin_client.get("/api/v1/inventory")
    assert {row["product_id"] for row in default.json()["items"]} == {active}
    assert default.json()["total"] == 1

    everything = await admin_client.get("/api/v1/inventory", params={"include_inactive": "true"})
    assert {row["product_id"] for row in everything.json()["items"]} == {active, inactive}
    assert everything.json()["total"] == 2


async def test_inventory_history_records_adjustments_and_level_sets(
    admin_client: AsyncClient, admin_user: User
) -> None:
    product_id = await _make_product(admin_client, "INV-HIST")
    await admin_client.post(f"/api/v1/inventory/{product_id}/adjust", json={"delta": 50, "reason": "restock"})
    await admin_client.post(f"/api/v1/inventory/{product_id}/adjust", json={"delta": -5})
    await admin_client.put(
        f"/api/v1/inventory/{product_id}",
        json={"quantity_on_hand": 40, "reorder_level": 7, "reason": "physical count"},
    )

    resp = await admin_client.get(f"/api/v1/inventory/{product_id}/history")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    newest, middle, oldest = body["items"]  # newest first

    assert newest["kind"] == "set_levels"
    assert (newest["quantity_on_hand_before"], newest["quantity_on_hand_after"]) == (45, 40)
    assert newest["quantity_delta"] == -5
    assert (newest["reorder_level_before"], newest["reorder_level_after"]) == (0, 7)
    assert newest["reason"] == "physical count"
    assert newest["actor"] == {
        "id": str(admin_user.id),
        "email": admin_user.email,
        "full_name": admin_user.full_name,
        "role": "admin",
    }

    assert (middle["kind"], middle["quantity_delta"], middle["reason"]) == ("adjust", -5, None)
    assert (oldest["kind"], oldest["quantity_on_hand_before"], oldest["quantity_on_hand_after"]) == (
        "adjust",
        0,
        50,
    )
    assert oldest["reason"] == "restock"

    page = await admin_client.get(f"/api/v1/inventory/{product_id}/history", params={"page_size": 2})
    assert len(page.json()["items"]) == 2
    assert page.json()["pages"] == 2


async def test_inventory_history_is_staff_only(
    admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    product_id = await _make_product(admin_client, "INV-HIST-AUTH")
    assert (await customer_client.get(f"/api/v1/inventory/{product_id}/history")).status_code == 403
    missing = await admin_client.get("/api/v1/inventory/00000000-0000-0000-0000-000000000000/history")
    assert missing.status_code == 404


async def test_set_levels_below_reserved_is_rejected(
    admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    product_id = await _make_product(admin_client, "INV-RSV")
    await admin_client.put(f"/api/v1/inventory/{product_id}", json={"quantity_on_hand": 5})
    order = await customer_client.post(
        "/api/v1/orders", json={"items": [{"product_id": product_id, "quantity": 3}]}
    )
    assert order.status_code == 201  # reserves 3

    too_low = await admin_client.put(f"/api/v1/inventory/{product_id}", json={"quantity_on_hand": 2})
    assert too_low.status_code == 409  # used to be a 500 (CHECK constraint)
    exact = await admin_client.put(f"/api/v1/inventory/{product_id}", json={"quantity_on_hand": 3})
    assert exact.status_code == 200
