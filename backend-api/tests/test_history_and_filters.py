"""Order status filter, staff-only inactive products, and the append-only
order/inventory history endpoints."""

from httpx import AsyncClient

from app.models.user import User

ADDRESS = {"line1": "Calle 1", "city": "Bogotá", "state": "DC", "postal_code": "110111", "country": "CO"}


async def _make_stocked_product(admin_client: AsyncClient, sku: str, stock: int = 10) -> str:
    category = await admin_client.post("/api/v1/categories", json={"name": f"Cat-{sku}"})
    product = await admin_client.post(
        "/api/v1/products",
        json={"sku": sku, "name": f"Product {sku}", "category_id": category.json()["id"], "price": "20.00"},
    )
    product_id = product.json()["id"]
    await admin_client.post(f"/api/v1/inventory/{product_id}/adjust", json={"delta": stock})
    return product_id


async def _order(customer_client: AsyncClient, product_id: str, *, pay: bool) -> str:
    address = await customer_client.post("/api/v1/customers/me/addresses", json=ADDRESS)
    order = await customer_client.post(
        "/api/v1/orders",
        json={
            "items": [{"product_id": product_id, "quantity": 1}],
            "shipping_address_id": address.json()["id"],
        },
    )
    order_id = order.json()["id"]
    if pay:
        paid = await customer_client.post("/api/v1/payments", json={"order_id": order_id, "method": "card"})
        assert paid.status_code == 201
    return order_id


# --- GET /orders?status= ------------------------------------------------------


async def test_order_status_filter_counts_and_repeats(
    admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    product_id = await _make_stocked_product(admin_client, "FLT-001")
    pending_id = await _order(customer_client, product_id, pay=False)
    paid_id = await _order(customer_client, product_id, pay=True)

    resp = await customer_client.get("/api/v1/orders", params={"status": "paid"})
    assert resp.status_code == 200
    body = resp.json()
    assert [o["id"] for o in body["items"]] == [paid_id]
    assert body["total"] == 1
    assert body["pages"] == 1

    both = await customer_client.get("/api/v1/orders", params=[("status", "paid"), ("status", "pending")])
    assert {o["id"] for o in both.json()["items"]} == {pending_id, paid_id}
    assert both.json()["total"] == 2

    staff = await admin_client.get("/api/v1/orders", params={"status": "pending"})
    staff_ids = {o["id"] for o in staff.json()["items"]}
    assert pending_id in staff_ids
    assert paid_id not in staff_ids
    assert all(o["status"] == "pending" for o in staff.json()["items"])


async def test_order_status_filter_rejects_unknown_status(customer_client: AsyncClient) -> None:
    resp = await customer_client.get("/api/v1/orders", params={"status": "awaiting_payment"})
    assert resp.status_code == 422


# --- GET /products?include_inactive=true --------------------------------------


async def test_include_inactive_is_staff_only(
    client: AsyncClient, admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    product_id = await _make_stocked_product(admin_client, "INA-001")
    await admin_client.patch(f"/api/v1/products/{product_id}", json={"is_active": False})

    public = await client.get("/api/v1/products", params={"search": "INA-001"})
    assert public.json()["items"] == []

    assert (await client.get("/api/v1/products", params={"include_inactive": "true"})).status_code == 401
    customer = await customer_client.get("/api/v1/products", params={"include_inactive": "true"})
    assert customer.status_code == 403

    staff = await admin_client.get(
        "/api/v1/products", params={"include_inactive": "true", "search": "INA-001"}
    )
    assert staff.status_code == 200
    assert [p["id"] for p in staff.json()["items"]] == [product_id]
    assert staff.json()["items"][0]["is_active"] is False


async def test_inventory_list_hides_inactive_products_by_default(admin_client: AsyncClient) -> None:
    product_id = await _make_stocked_product(admin_client, "INA-002")
    await admin_client.patch(f"/api/v1/products/{product_id}", json={"is_active": False})

    async def ids(**params: str) -> set[str]:
        resp = await admin_client.get("/api/v1/inventory", params={"page_size": "100", **params})
        assert resp.status_code == 200
        pages = resp.json()["pages"]
        found = {row["product_id"] for row in resp.json()["items"]}
        for page in range(2, pages + 1):
            more = await admin_client.get(
                "/api/v1/inventory", params={"page_size": "100", "page": str(page), **params}
            )
            found |= {row["product_id"] for row in more.json()["items"]}
        return found

    assert product_id not in await ids()
    assert product_id in await ids(include_inactive="true")


# --- GET /orders/{id}/history ---------------------------------------------------


async def test_order_history_records_every_step_with_actor_and_source(
    admin_client: AsyncClient, customer_client: AsyncClient, admin_user: User, customer_user: User
) -> None:
    product_id = await _make_stocked_product(admin_client, "HIS-001")
    order_id = await _order(customer_client, product_id, pay=True)
    address_id = (await admin_client.get(f"/api/v1/orders/{order_id}")).json()["shipping_address_id"]

    shipment = await admin_client.post(
        f"/api/v1/shipments/order/{order_id}",
        json={"address_id": address_id, "carrier": "Servientrega", "tracking_number": "G-1"},
    )
    assert shipment.status_code == 201
    shipment_id = shipment.json()["id"]
    assert (await admin_client.post(f"/api/v1/shipments/{shipment_id}/ship")).status_code == 200
    assert (await admin_client.post(f"/api/v1/shipments/{shipment_id}/deliver")).status_code == 200

    resp = await admin_client.get(f"/api/v1/orders/{order_id}/history")
    assert resp.status_code == 200
    steps = [(c["from_status"], c["to_status"], c["source"]) for c in resp.json()]
    assert steps == [
        (None, "pending", "order_created"),
        ("pending", "paid", "payment"),
        ("paid", "preparing", "shipment_created"),
        ("preparing", "shipped", "shipment_dispatched"),
        ("shipped", "delivered", "shipment_delivered"),
    ]
    actors = [c["actor"]["email"] for c in resp.json()]
    assert actors[:2] == [customer_user.email, customer_user.email]
    assert actors[2:] == [admin_user.email] * 3


async def test_order_history_manual_and_customer_cancel(
    admin_client: AsyncClient, customer_client: AsyncClient, admin_user: User
) -> None:
    product_id = await _make_stocked_product(admin_client, "HIS-002")
    manual_id = await _order(customer_client, product_id, pay=True)
    patched = await admin_client.patch(f"/api/v1/orders/{manual_id}/status", json={"status": "preparing"})
    assert patched.status_code == 200
    last = (await admin_client.get(f"/api/v1/orders/{manual_id}/history")).json()[-1]
    assert (last["from_status"], last["to_status"], last["source"]) == ("paid", "preparing", "manual")
    assert last["actor"]["email"] == admin_user.email
    assert last["actor"]["role"] == "admin"

    cancel_id = await _order(customer_client, product_id, pay=False)
    assert (await customer_client.post(f"/api/v1/orders/{cancel_id}/cancel")).status_code == 200
    last = (await admin_client.get(f"/api/v1/orders/{cancel_id}/history")).json()[-1]
    assert (last["to_status"], last["source"]) == ("cancelled", "customer_cancel")


async def test_order_history_is_staff_only(admin_client: AsyncClient, customer_client: AsyncClient) -> None:
    product_id = await _make_stocked_product(admin_client, "HIS-003")
    order_id = await _order(customer_client, product_id, pay=False)
    assert (await customer_client.get(f"/api/v1/orders/{order_id}/history")).status_code == 403


# --- GET /inventory/{id}/history and PUT /inventory 409 -------------------------


async def test_inventory_history_keeps_reason_and_values(admin_client: AsyncClient, admin_user: User) -> None:
    product_id = await _make_stocked_product(admin_client, "INV-H01", stock=10)
    adjust = await admin_client.post(
        f"/api/v1/inventory/{product_id}/adjust", json={"delta": -3, "reason": "Producto dañado"}
    )
    assert adjust.status_code == 200
    put = await admin_client.put(
        f"/api/v1/inventory/{product_id}",
        json={"quantity_on_hand": 20, "reorder_level": 4, "reason": "Conteo"},
    )
    assert put.status_code == 200

    resp = await admin_client.get(f"/api/v1/inventory/{product_id}/history")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert resp.json()["total"] == 3  # initial restock + adjust + set_levels
    newest, adjusted = items[0], items[1]
    assert newest["kind"] == "set_levels"
    assert (newest["quantity_on_hand_before"], newest["quantity_on_hand_after"]) == (7, 20)
    assert newest["reorder_level_after"] == 4
    assert newest["reason"] == "Conteo"
    assert adjusted["kind"] == "adjust"
    assert adjusted["quantity_delta"] == -3
    assert adjusted["reason"] == "Producto dañado"
    assert adjusted["actor"]["email"] == admin_user.email


async def test_inventory_history_is_staff_only(
    admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    product_id = await _make_stocked_product(admin_client, "INV-H02")
    assert (await customer_client.get(f"/api/v1/inventory/{product_id}/history")).status_code == 403


async def test_set_levels_below_reserved_returns_409(
    admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    product_id = await _make_stocked_product(admin_client, "INV-H03", stock=5)
    await _order(customer_client, product_id, pay=False)  # reserves 1
    resp = await admin_client.put(f"/api/v1/inventory/{product_id}", json={"quantity_on_hand": 0})
    assert resp.status_code == 409
    inv = (await admin_client.get(f"/api/v1/inventory/{product_id}")).json()
    assert inv["quantity_on_hand"] == 5
