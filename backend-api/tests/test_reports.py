from httpx import AsyncClient


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


async def _pay_order(customer_client: AsyncClient, order_id: str) -> None:
    resp = await customer_client.post("/api/v1/payments", json={"order_id": order_id, "method": "card"})
    assert resp.status_code == 201


async def test_report_summary_requires_staff(customer_client: AsyncClient) -> None:
    resp = await customer_client.get("/api/v1/reports/summary")
    assert resp.status_code == 403


async def test_report_summary_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/reports/summary")
    assert resp.status_code == 401


async def test_report_summary_reflects_paid_orders_only(
    admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    product_id = await _make_stocked_product(admin_client, "RPT-001", stock=10, price="50.00")

    paid = await customer_client.post(
        "/api/v1/orders", json={"items": [{"product_id": product_id, "quantity": 2}]}
    )
    await _pay_order(customer_client, paid.json()["id"])

    # An unpaid order must not count toward revenue or units sold.
    await customer_client.post("/api/v1/orders", json={"items": [{"product_id": product_id, "quantity": 3}]})

    resp = await admin_client.get("/api/v1/reports/summary")
    assert resp.status_code == 200
    body = resp.json()

    assert float(body["net_revenue"]) >= 100.00
    assert body["sale_count"] >= 1
    assert body["customer_count"] >= 1
    assert body["product_count"] >= 1

    status_counts = {row["status"]: row["count"] for row in body["orders_by_status"]}
    assert status_counts["paid"] >= 1
    assert status_counts["pending"] >= 1

    top = {row["sku"]: row for row in body["top_products"]}
    assert "RPT-001" in top
    assert top["RPT-001"]["units_sold"] >= 2


async def test_report_summary_is_net_of_cancelled_and_refunded_orders(
    admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    product_id = await _make_stocked_product(admin_client, "RPT-NET", stock=20, price="50.00")

    async def paid_order(quantity: int) -> str:
        order = await customer_client.post(
            "/api/v1/orders", json={"items": [{"product_id": product_id, "quantity": quantity}]}
        )
        await _pay_order(customer_client, order.json()["id"])
        return order.json()["id"]

    await paid_order(2)  # kept: 100.00
    refunded = await paid_order(1)  # 50.00, refunded from `paid`
    cancelled = await paid_order(3)  # 150.00, cancelled from `preparing`
    unpaid = await customer_client.post(
        "/api/v1/orders", json={"items": [{"product_id": product_id, "quantity": 1}]}
    )

    async def set_status(order_id: str, status: str) -> None:
        resp = await admin_client.patch(f"/api/v1/orders/{order_id}/status", json={"status": status})
        assert resp.status_code == 200

    await set_status(refunded, "refunded")
    await set_status(cancelled, "preparing")
    await set_status(cancelled, "cancelled")
    await set_status(unpaid.json()["id"], "cancelled")  # never paid: no ledger entry at all

    body = (await admin_client.get("/api/v1/reports/summary")).json()
    # Each test runs in its own rolled-back transaction, so these are exact.
    assert body["gross_revenue"] == "300.00"
    assert body["refunded_amount"] == "200.00"
    assert body["net_revenue"] == "100.00"
    assert body["sale_count"] == 3
    assert body["reversal_count"] == 2

    top = {row["sku"]: row for row in body["top_products"]}
    assert top["RPT-NET"]["units_sold"] == 2
    assert top["RPT-NET"]["revenue"] == "100.00"


async def test_report_summary_money_fields_are_2dp_when_ledger_is_empty(admin_client: AsyncClient) -> None:
    body = (await admin_client.get("/api/v1/reports/summary")).json()
    assert body["net_revenue"] == "0.00"
    assert body["gross_revenue"] == "0.00"
    assert body["refunded_amount"] == "0.00"
    assert body["sale_count"] == 0
    assert body["reversal_count"] == 0


async def test_report_summary_top_products_limit(
    admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    for i in range(3):
        product_id = await _make_stocked_product(admin_client, f"RPT-LIM-{i}", stock=5)
        order = await customer_client.post(
            "/api/v1/orders", json={"items": [{"product_id": product_id, "quantity": 1}]}
        )
        await _pay_order(customer_client, order.json()["id"])

    resp = await admin_client.get("/api/v1/reports/summary", params={"top_products_limit": 2})
    assert resp.status_code == 200
    assert len(resp.json()["top_products"]) <= 2
