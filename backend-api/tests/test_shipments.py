from httpx import AsyncClient


async def _make_stocked_product(admin_client: AsyncClient, sku: str, stock: int, price: str = "20.00") -> str:
    category = await admin_client.post("/api/v1/categories", json={"name": f"Cat-{sku}"})
    category_id = category.json()["id"]
    product = await admin_client.post(
        "/api/v1/products",
        json={"sku": sku, "name": f"Product {sku}", "category_id": category_id, "price": price},
    )
    product_id = product.json()["id"]
    await admin_client.post(f"/api/v1/inventory/{product_id}/adjust", json={"delta": stock})
    return product_id


async def _order_with_address(
    admin_client: AsyncClient, customer_client: AsyncClient, sku: str, *, quantity: int = 2, pay: bool = True
) -> tuple[str, str, str]:
    """Returns (order_id, product_id, address_id) for an order of `quantity`
    units from a product stocked with 10, paid unless `pay=False`."""
    product_id = await _make_stocked_product(admin_client, sku, stock=10)
    address = await customer_client.post(
        "/api/v1/customers/me/addresses",
        json={"line1": "Calle 1", "city": "Bogotá", "state": "DC", "postal_code": "110111", "country": "CO"},
    )
    address_id = address.json()["id"]
    order = await customer_client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": product_id, "quantity": quantity}], "shipping_address_id": address_id},
    )
    order_id = order.json()["id"]
    if pay:
        paid = await customer_client.post("/api/v1/payments", json={"order_id": order_id, "method": "card"})
        assert paid.status_code == 201
    return order_id, product_id, address_id


async def _inventory(admin_client: AsyncClient, product_id: str) -> tuple[int, int]:
    body = (await admin_client.get(f"/api/v1/inventory/{product_id}")).json()
    return body["quantity_on_hand"], body["quantity_reserved"]


async def test_create_shipment_on_paid_order_with_carrier_and_tracking(
    admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    order_id, _, address_id = await _order_with_address(admin_client, customer_client, "SHP-001")

    resp = await admin_client.post(
        f"/api/v1/shipments/order/{order_id}",
        json={"address_id": address_id, "carrier": "DHL", "tracking_number": "TRK-001"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "preparing"
    assert body["carrier"] == "DHL"
    assert body["tracking_number"] == "TRK-001"

    order = await admin_client.get(f"/api/v1/orders/{order_id}")
    assert order.json()["status"] == "preparing"


async def test_create_shipment_when_order_already_preparing(
    admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    """The reported bug: staff moved the order to `preparing` by hand first,
    then could never create the shipment to attach the tracking number."""
    order_id, _, address_id = await _order_with_address(admin_client, customer_client, "SHP-002")
    manual = await admin_client.patch(f"/api/v1/orders/{order_id}/status", json={"status": "preparing"})
    assert manual.status_code == 200

    resp = await admin_client.post(
        f"/api/v1/shipments/order/{order_id}",
        json={"address_id": address_id, "tracking_number": "TRK-002"},
    )
    assert resp.status_code == 201
    assert resp.json()["tracking_number"] == "TRK-002"

    order = await admin_client.get(f"/api/v1/orders/{order_id}")
    assert order.json()["status"] == "preparing"


async def test_create_shipment_rejects_unpaid_order(
    admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    order_id, _, address_id = await _order_with_address(admin_client, customer_client, "SHP-003", pay=False)

    resp = await admin_client.post(f"/api/v1/shipments/order/{order_id}", json={"address_id": address_id})
    assert resp.status_code == 409


async def test_second_shipment_for_same_order_conflicts(
    admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    order_id, _, address_id = await _order_with_address(admin_client, customer_client, "SHP-004")
    first = await admin_client.post(f"/api/v1/shipments/order/{order_id}", json={"address_id": address_id})
    assert first.status_code == 201

    second = await admin_client.post(f"/api/v1/shipments/order/{order_id}", json={"address_id": address_id})
    assert second.status_code == 409


async def test_edit_carrier_and_tracking_before_dispatch(
    admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    order_id, _, address_id = await _order_with_address(admin_client, customer_client, "SHP-005")
    created = await admin_client.post(
        f"/api/v1/shipments/order/{order_id}",
        json={"address_id": address_id, "carrier": "DHL", "tracking_number": "   "},
    )
    shipment_id = created.json()["id"]
    assert created.json()["tracking_number"] is None  # blank means "not set"

    edited = await admin_client.patch(f"/api/v1/shipments/{shipment_id}", json={"tracking_number": "TRK-005"})
    assert edited.status_code == 200
    assert edited.json()["tracking_number"] == "TRK-005"
    assert edited.json()["carrier"] == "DHL"  # not sent, so unchanged

    cleared = await admin_client.patch(
        f"/api/v1/shipments/{shipment_id}", json={"carrier": None, "tracking_number": "TRK-005B"}
    )
    assert cleared.status_code == 200
    assert cleared.json()["carrier"] is None
    assert cleared.json()["tracking_number"] == "TRK-005B"


async def test_ship_keeps_tracking_number_and_fulfills_stock_once(
    admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    order_id, product_id, address_id = await _order_with_address(
        admin_client, customer_client, "SHP-006", quantity=3
    )
    created = await admin_client.post(
        f"/api/v1/shipments/order/{order_id}", json={"address_id": address_id, "tracking_number": "TRK-006"}
    )
    shipment_id = created.json()["id"]
    assert await _inventory(admin_client, product_id) == (10, 3)

    shipped = await admin_client.post(f"/api/v1/shipments/{shipment_id}/ship")
    assert shipped.status_code == 200
    assert shipped.json()["status"] == "in_transit"
    assert shipped.json()["tracking_number"] == "TRK-006"
    assert await _inventory(admin_client, product_id) == (7, 0)

    again = await admin_client.post(f"/api/v1/shipments/{shipment_id}/ship")
    assert again.status_code == 409
    assert await _inventory(admin_client, product_id) == (7, 0)

    order = await admin_client.get(f"/api/v1/orders/{order_id}")
    assert order.json()["status"] == "shipped"


async def test_ship_without_tracking_number_generates_one(
    admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    order_id, _, address_id = await _order_with_address(admin_client, customer_client, "SHP-007")
    created = await admin_client.post(f"/api/v1/shipments/order/{order_id}", json={"address_id": address_id})
    assert created.json()["tracking_number"] is None

    shipped = await admin_client.post(f"/api/v1/shipments/{created.json()['id']}/ship")
    assert shipped.status_code == 200
    assert shipped.json()["tracking_number"].startswith("MANUAL-")


async def test_edit_after_dispatch_is_rejected(
    admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    order_id, _, address_id = await _order_with_address(admin_client, customer_client, "SHP-008")
    created = await admin_client.post(f"/api/v1/shipments/order/{order_id}", json={"address_id": address_id})
    shipment_id = created.json()["id"]
    await admin_client.post(f"/api/v1/shipments/{shipment_id}/ship")

    resp = await admin_client.patch(f"/api/v1/shipments/{shipment_id}", json={"tracking_number": "LATE"})
    assert resp.status_code == 409


async def test_cancelling_preparing_order_cancels_its_shipment_and_releases_stock(
    admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    order_id, product_id, address_id = await _order_with_address(admin_client, customer_client, "SHP-009")
    created = await admin_client.post(f"/api/v1/shipments/order/{order_id}", json={"address_id": address_id})
    shipment_id = created.json()["id"]

    cancelled = await admin_client.patch(f"/api/v1/orders/{order_id}/status", json={"status": "cancelled"})
    assert cancelled.status_code == 200

    shipment = await admin_client.get(f"/api/v1/shipments/order/{order_id}")
    assert shipment.json()["status"] == "cancelled"
    assert await _inventory(admin_client, product_id) == (10, 0)

    # A cancelled shipment can be neither dispatched nor edited.
    assert (await admin_client.post(f"/api/v1/shipments/{shipment_id}/ship")).status_code == 409
    edit = await admin_client.patch(f"/api/v1/shipments/{shipment_id}", json={"tracking_number": "X"})
    assert edit.status_code == 409
    assert await _inventory(admin_client, product_id) == (10, 0)


async def test_deliver_requires_dispatch(admin_client: AsyncClient, customer_client: AsyncClient) -> None:
    order_id, _, address_id = await _order_with_address(admin_client, customer_client, "SHP-010")
    created = await admin_client.post(f"/api/v1/shipments/order/{order_id}", json={"address_id": address_id})

    resp = await admin_client.post(f"/api/v1/shipments/{created.json()['id']}/deliver")
    assert resp.status_code == 409


async def test_manual_status_change_cannot_ship_or_deliver(
    admin_client: AsyncClient, customer_client: AsyncClient
) -> None:
    order_id, _, _ = await _order_with_address(admin_client, customer_client, "SHP-011")
    await admin_client.patch(f"/api/v1/orders/{order_id}/status", json={"status": "preparing"})

    shipped = await admin_client.patch(f"/api/v1/orders/{order_id}/status", json={"status": "shipped"})
    assert shipped.status_code == 409
    delivered = await admin_client.patch(f"/api/v1/orders/{order_id}/status", json={"status": "delivered"})
    assert delivered.status_code == 409
