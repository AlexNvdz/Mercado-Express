from httpx import AsyncClient

from app.models.user import User


async def _paid_order(admin_client: AsyncClient, customer_client: AsyncClient, sku: str) -> tuple[str, str]:
    """Returns (order_id, address_id) for a paid order of 1 unit."""
    category = await admin_client.post("/api/v1/categories", json={"name": f"Cat-{sku}"})
    product = await admin_client.post(
        "/api/v1/products",
        json={"sku": sku, "name": sku, "category_id": category.json()["id"], "price": "12.00"},
    )
    product_id = product.json()["id"]
    await admin_client.post(f"/api/v1/inventory/{product_id}/adjust", json={"delta": 5})
    address = await customer_client.post(
        "/api/v1/customers/me/addresses",
        json={"line1": "Calle 1", "city": "Bogotá", "state": "DC", "postal_code": "110111", "country": "CO"},
    )
    address_id = address.json()["id"]
    order = await customer_client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": product_id, "quantity": 1}], "shipping_address_id": address_id},
    )
    order_id = order.json()["id"]
    paid = await customer_client.post("/api/v1/payments", json={"order_id": order_id, "method": "card"})
    assert paid.status_code == 201
    return order_id, address_id


async def _history(admin_client: AsyncClient, order_id: str) -> list[tuple[str | None, str, str, str | None]]:
    """(from_status, to_status, source, actor email) per entry, oldest first."""
    resp = await admin_client.get(f"/api/v1/orders/{order_id}/history")
    assert resp.status_code == 200
    return [
        (e["from_status"], e["to_status"], e["source"], e["actor"]["email"] if e["actor"] else None)
        for e in resp.json()
    ]


async def test_history_follows_the_whole_order_lifecycle(
    admin_client: AsyncClient, customer_client: AsyncClient, admin_user: User, customer_user: User
) -> None:
    order_id, address_id = await _paid_order(admin_client, customer_client, "HIST-001")
    shipment = await admin_client.post(f"/api/v1/shipments/order/{order_id}", json={"address_id": address_id})
    shipment_id = shipment.json()["id"]
    await admin_client.post(f"/api/v1/shipments/{shipment_id}/ship")
    await admin_client.post(f"/api/v1/shipments/{shipment_id}/deliver")

    assert await _history(admin_client, order_id) == [
        (None, "pending", "order_created", customer_user.email),
        ("pending", "paid", "payment", customer_user.email),
        ("paid", "preparing", "shipment_created", admin_user.email),
        ("preparing", "shipped", "shipment_dispatched", admin_user.email),
        ("shipped", "delivered", "shipment_delivered", admin_user.email),
    ]

    entry = (await admin_client.get(f"/api/v1/orders/{order_id}/history")).json()[2]
    assert entry["order_id"] == order_id
    assert entry["actor"]["role"] == "admin"
    assert entry["created_at"]


async def test_manual_change_is_recorded_and_shipment_creation_adds_no_duplicate(
    admin_client: AsyncClient, customer_client: AsyncClient, admin_user: User
) -> None:
    order_id, address_id = await _paid_order(admin_client, customer_client, "HIST-002")
    await admin_client.patch(f"/api/v1/orders/{order_id}/status", json={"status": "preparing"})
    # The order is already `preparing`: creating the shipment changes no status.
    await admin_client.post(f"/api/v1/shipments/order/{order_id}", json={"address_id": address_id})
    await admin_client.patch(f"/api/v1/orders/{order_id}/status", json={"status": "cancelled"})

    history = await _history(admin_client, order_id)
    assert [(f, t, s) for f, t, s, _ in history] == [
        (None, "pending", "order_created"),
        ("pending", "paid", "payment"),
        ("paid", "preparing", "manual"),
        ("preparing", "cancelled", "manual"),
    ]
    assert history[2][3] == admin_user.email
    assert history[3][3] == admin_user.email


async def test_customer_cancel_is_recorded_with_the_customer_as_actor(
    admin_client: AsyncClient, customer_client: AsyncClient, customer_user: User
) -> None:
    category = await admin_client.post("/api/v1/categories", json={"name": "Cat-HIST-003"})
    product = await admin_client.post(
        "/api/v1/products",
        json={"sku": "HIST-003", "name": "x", "category_id": category.json()["id"], "price": "1.00"},
    )
    await admin_client.post(f"/api/v1/inventory/{product.json()['id']}/adjust", json={"delta": 1})
    order = await customer_client.post(
        "/api/v1/orders", json={"items": [{"product_id": product.json()["id"], "quantity": 1}]}
    )
    order_id = order.json()["id"]
    await customer_client.post(f"/api/v1/orders/{order_id}/cancel")

    assert await _history(admin_client, order_id) == [
        (None, "pending", "order_created", customer_user.email),
        ("pending", "cancelled", "customer_cancel", customer_user.email),
    ]


async def test_refund_and_rejected_transition(
    admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    order_id, _ = await _paid_order(admin_client, customer_client, "HIST-004")
    rejected = await admin_client.patch(f"/api/v1/orders/{order_id}/status", json={"status": "shipped"})
    assert rejected.status_code == 409
    await admin_client.patch(f"/api/v1/orders/{order_id}/status", json={"status": "refunded"})

    # The rejected attempt leaves no trace; the refund does.
    assert [(f, t, s) for f, t, s, _ in await _history(admin_client, order_id)] == [
        (None, "pending", "order_created"),
        ("pending", "paid", "payment"),
        ("paid", "refunded", "manual"),
    ]


async def test_order_history_is_staff_only(
    client: AsyncClient, admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    order_id, _ = await _paid_order(admin_client, customer_client, "HIST-005")
    assert (await client.get(f"/api/v1/orders/{order_id}/history")).status_code == 401
    assert (await customer_client.get(f"/api/v1/orders/{order_id}/history")).status_code == 403
    missing = await admin_client.get("/api/v1/orders/00000000-0000-0000-0000-000000000000/history")
    assert missing.status_code == 404
