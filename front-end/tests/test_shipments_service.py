import pytest

from services import mock_data, orders, shipments
from services.exceptions import ApiConflictError


def test_get_shipment_for_shipped_order():
    order_id = mock_data.MOCK_ORDERS[1]["id"]  # seeded as "shipped" in mock_data
    shipment = shipments.get_shipment_for_order("any", order_id)
    assert shipment is not None
    assert shipment["tracking_number"]


def test_get_shipment_for_order_without_shipment():
    assert shipments.get_shipment_for_order("any", "00000000-0000-0000-0000-000000000999") is None


def _paid_order():
    order = orders.create_order(
        "any",
        [{"product_id": mock_data.MOCK_PRODUCTS[0]["id"], "quantity": 1}],
        shipping_address_id=mock_data.MOCK_ADDRESSES[0]["id"],
    )
    order["status"] = "paid"
    return order


def test_seeded_shipments_use_shipment_status_vocabulary():
    for shipment in mock_data.MOCK_SHIPMENTS.values():
        assert shipment["status"] in shipments.SHIPMENT_STATUS_LABELS


def test_cancelled_shipment_has_spanish_label():
    assert shipments.SHIPMENT_STATUS_LABELS["cancelled"] == "Cancelado"


@pytest.mark.parametrize("status,allowed", [("pending", False), ("paid", True), ("preparing", True), ("shipped", False)])
def test_can_create_shipment_only_for_paid_or_preparing(status, allowed):
    assert shipments.can_create_shipment(status) is allowed


def test_create_shipment_twice_conflicts():
    order = _paid_order()
    shipments.create_shipment("any", order["id"], order["shipping_address_id"])
    with pytest.raises(ApiConflictError):
        shipments.create_shipment("any", order["id"], order["shipping_address_id"])


def test_ship_generates_tracking_number_only_when_missing():
    order = _paid_order()
    shipment = shipments.create_shipment("any", order["id"], order["shipping_address_id"])
    assert shipment["tracking_number"] is None
    shipped = shipments.ship_shipment("any", shipment["id"], order["id"])
    assert shipped["tracking_number"].startswith("MANUAL-")


def test_ship_requires_preparing_order():
    order = _paid_order()
    shipment = shipments.create_shipment("any", order["id"], order["shipping_address_id"])
    order["status"] = "cancelled"
    with pytest.raises(ApiConflictError):
        shipments.ship_shipment("any", shipment["id"], order["id"])


# --- Real-API request shapes (see the api_calls fixture in conftest.py) ---


def test_create_shipment_sends_tracking_number(api_calls):
    shipments.create_shipment("tok", "order-1", "addr-1", carrier="DHL", tracking_number="DHL-1")
    method, path, kwargs = api_calls[0]
    assert (method, path) == ("POST", "/api/v1/shipments/order/order-1")
    assert kwargs["json"] == {"address_id": "addr-1", "carrier": "DHL", "tracking_number": "DHL-1"}


def test_update_shipment_patches_shipment(api_calls):
    shipments.update_shipment("tok", "ship-1", "order-1", carrier=None, tracking_number="T-2")
    method, path, kwargs = api_calls[0]
    assert (method, path) == ("PATCH", "/api/v1/shipments/ship-1")
    assert kwargs["json"] == {"carrier": None, "tracking_number": "T-2"}
