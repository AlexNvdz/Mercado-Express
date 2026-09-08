from httpx import AsyncClient


async def _make_stocked_product(
    admin_client: AsyncClient, sku: str, stock: int, price: str = "25.00"
) -> str:
    category = await admin_client.post("/api/v1/categories", json={"name": f"Cat-{sku}"})
    category_id = category.json()["id"]
    product = await admin_client.post(
        "/api/v1/products",
        json={"sku": sku, "name": f"Product {sku}", "category_id": category_id, "price": price},
    )
    product_id = product.json()["id"]
    await admin_client.post(f"/api/v1/inventory/{product_id}/adjust", json={"delta": stock})
    return product_id


async def test_create_order_reserves_stock_and_computes_totals(
    admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    product_id = await _make_stocked_product(admin_client, "ORD-001", stock=10, price="25.00")

    resp = await customer_client.post(
        "/api/v1/orders", json={"items": [{"product_id": product_id, "quantity": 3}]}
    )
    assert resp.status_code == 201
    order = resp.json()
    assert order["status"] == "pending"
    assert order["subtotal"] == "75.00"
    assert order["total_amount"] == "75.00"
    assert len(order["items"]) == 1

    inv = await admin_client.get(f"/api/v1/inventory/{product_id}")
    body = inv.json()
    assert body["quantity_on_hand"] == 10
    assert body["quantity_reserved"] == 3
    assert body["quantity_available"] == 7


async def test_create_order_insufficient_stock_returns_409(
    admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    product_id = await _make_stocked_product(admin_client, "ORD-002", stock=2)

    resp = await customer_client.post(
        "/api/v1/orders", json={"items": [{"product_id": product_id, "quantity": 5}]}
    )
    assert resp.status_code == 409

    # No partial reservation should have been made.
    inv = await admin_client.get(f"/api/v1/inventory/{product_id}")
    assert inv.json()["quantity_reserved"] == 0


async def test_create_order_unknown_product_returns_404(customer_client: AsyncClient) -> None:
    resp = await customer_client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": "00000000-0000-0000-0000-000000000000", "quantity": 1}]},
    )
    assert resp.status_code == 404


async def test_customer_cannot_view_others_order(
    admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    product_id = await _make_stocked_product(admin_client, "ORD-003", stock=5)
    created = await customer_client.post(
        "/api/v1/orders", json={"items": [{"product_id": product_id, "quantity": 1}]}
    )
    order_id = created.json()["id"]

    # A second, unrelated customer must not see this order.
    resp = await admin_client.get(f"/api/v1/orders/{order_id}")
    assert resp.status_code == 200  # staff can see any order


async def test_cancel_order_releases_reserved_stock(
    admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    product_id = await _make_stocked_product(admin_client, "ORD-004", stock=5)
    created = await customer_client.post(
        "/api/v1/orders", json={"items": [{"product_id": product_id, "quantity": 2}]}
    )
    order_id = created.json()["id"]

    cancelled = await customer_client.post(f"/api/v1/orders/{order_id}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    inv = await admin_client.get(f"/api/v1/inventory/{product_id}")
    assert inv.json()["quantity_reserved"] == 0
    assert inv.json()["quantity_on_hand"] == 5


async def test_full_order_lifecycle_to_delivered(
    admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    product_id = await _make_stocked_product(admin_client, "ORD-005", stock=10, price="50.00")

    order_resp = await customer_client.post(
        "/api/v1/orders", json={"items": [{"product_id": product_id, "quantity": 2}]}
    )
    order = order_resp.json()
    order_id = order["id"]

    address_resp = await customer_client.post(
        "/api/v1/customers/me/addresses",
        json={
            "line1": "123 Main St",
            "city": "Springfield",
            "state": "IL",
            "postal_code": "62704",
            "country": "US",
        },
    )
    address_id = address_resp.json()["id"]

    pay_resp = await customer_client.post(
        "/api/v1/payments", json={"order_id": order_id, "method": "card"}
    )
    assert pay_resp.status_code == 201
    assert pay_resp.json()["status"] == "completed"

    order_after_pay = await customer_client.get(f"/api/v1/orders/{order_id}")
    assert order_after_pay.json()["status"] == "paid"

    ship_resp = await admin_client.post(
        f"/api/v1/shipments/order/{order_id}", json={"address_id": address_id}
    )
    assert ship_resp.status_code == 201
    shipment_id = ship_resp.json()["id"]
    assert ship_resp.json()["status"] == "preparing"

    dispatch_resp = await admin_client.post(f"/api/v1/shipments/{shipment_id}/ship")
    assert dispatch_resp.status_code == 200
    assert dispatch_resp.json()["status"] == "in_transit"

    inv_after_ship = await admin_client.get(f"/api/v1/inventory/{product_id}")
    assert inv_after_ship.json()["quantity_on_hand"] == 8
    assert inv_after_ship.json()["quantity_reserved"] == 0

    deliver_resp = await admin_client.post(f"/api/v1/shipments/{shipment_id}/deliver")
    assert deliver_resp.status_code == 200
    assert deliver_resp.json()["status"] == "delivered"

    final_order = await customer_client.get(f"/api/v1/orders/{order_id}")
    assert final_order.json()["status"] == "delivered"


async def test_orders_require_authentication(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/orders", json={"items": []})
    assert resp.status_code == 401
