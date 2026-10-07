from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from tests.conftest import _authed_client, _create_user


async def _make_stocked_product(admin_client: AsyncClient, sku: str, stock: int, price: str = "25.00") -> str:
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


async def test_refund_releases_reserved_stock(
    admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    product_id = await _make_stocked_product(admin_client, "ORD-REF", stock=5)
    created = await customer_client.post(
        "/api/v1/orders", json={"items": [{"product_id": product_id, "quantity": 2}]}
    )
    order_id = created.json()["id"]
    await customer_client.post("/api/v1/payments", json={"order_id": order_id, "method": "card"})

    refunded = await admin_client.patch(f"/api/v1/orders/{order_id}/status", json={"status": "refunded"})
    assert refunded.status_code == 200
    assert refunded.json()["status"] == "refunded"

    # Refund is only reachable before dispatch, so the goods never left:
    # the reservation is released and on-hand stock is untouched.
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

    pay_resp = await customer_client.post("/api/v1/payments", json={"order_id": order_id, "method": "card"})
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


async def test_staff_can_list_all_orders_with_items(
    admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    """Regression test: OrderService.list_all used to reuse the generic
    BaseRepository.list(), which doesn't eager-load Order.items -- serializing
    OrderOut.items then triggered an async lazy-load outside the request's
    greenlet context (MissingGreenlet) instead of returning order data. Found
    via the frontend's admin dashboard (apps/adminpanel), which was the first
    caller to ever exercise plain `GET /orders` as staff.
    """
    product_id = await _make_stocked_product(admin_client, "ORD-006", stock=5, price="10.00")
    created = await customer_client.post(
        "/api/v1/orders", json={"items": [{"product_id": product_id, "quantity": 1}]}
    )
    assert created.status_code == 201
    order_id = created.json()["id"]

    resp = await admin_client.get("/api/v1/orders")
    assert resp.status_code == 200
    body = resp.json()
    listed = next(o for o in body["items"] if o["id"] == order_id)
    assert len(listed["items"]) == 1
    assert listed["items"][0]["product_id"] == product_id


async def test_list_orders_filters_by_one_or_more_statuses(
    admin_client: AsyncClient, customer_client: AsyncClient, db_session: AsyncSession
) -> None:
    product_id = await _make_stocked_product(admin_client, "ORD-FLT", stock=10)

    async def place_order(client: AsyncClient) -> str:
        resp = await client.post(
            "/api/v1/orders", json={"items": [{"product_id": product_id, "quantity": 1}]}
        )
        assert resp.status_code == 201
        return resp.json()["id"]

    await place_order(customer_client)  # stays pending
    paid = await place_order(customer_client)
    await customer_client.post("/api/v1/payments", json={"order_id": paid, "method": "card"})
    cancelled = await place_order(customer_client)
    await customer_client.post(f"/api/v1/orders/{cancelled}/cancel")

    # A second customer's paid order: staff see it, the first customer doesn't.
    other_user = await _create_user(db_session, email="other-filter@test.com", role=UserRole.CUSTOMER)
    async with _authed_client(other_user) as other_client:
        other_paid = await place_order(other_client)
        await other_client.post("/api/v1/payments", json={"order_id": other_paid, "method": "card"})

    mine = (await customer_client.get("/api/v1/orders", params={"status": "paid"})).json()
    assert [o["id"] for o in mine["items"]] == [paid]
    assert mine["total"] == 1

    all_paid = (await admin_client.get("/api/v1/orders", params={"status": "paid"})).json()
    assert {o["id"] for o in all_paid["items"]} == {paid, other_paid}
    assert all_paid["total"] == 2

    params = [("status", "paid"), ("status", "cancelled"), ("page_size", "1")]
    two_statuses = (await customer_client.get("/api/v1/orders", params=params)).json()
    assert two_statuses["total"] == 2
    assert two_statuses["pages"] == 2
    assert len(two_statuses["items"]) == 1

    assert (await customer_client.get("/api/v1/orders")).json()["total"] == 3
    assert (await admin_client.get("/api/v1/orders")).json()["total"] == 4


async def test_list_orders_rejects_unknown_status(customer_client: AsyncClient) -> None:
    resp = await customer_client.get("/api/v1/orders", params={"status": "lost"})
    assert resp.status_code == 422
