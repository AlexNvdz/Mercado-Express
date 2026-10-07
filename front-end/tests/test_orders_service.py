import pytest

from services import mock_data, orders
from services.exceptions import ApiConflictError

ARROZ_ID = mock_data.MOCK_PRODUCTS[0]["id"]
ADDRESS_ID = mock_data.MOCK_ADDRESSES[0]["id"]


def test_list_orders_returns_envelope():
    result = orders.list_orders(token="any")
    assert "items" in result
    assert len(result["items"]) >= 2


def test_get_order_found():
    order_id = mock_data.MOCK_ORDERS[0]["id"]
    order = orders.get_order(token="any", order_id=order_id)
    assert order is not None
    assert order["id"] == order_id


def test_get_order_not_found():
    assert orders.get_order(token="any", order_id="00000000-0000-0000-0000-000000000999") is None


def test_create_order_computes_totals_from_catalog():
    items = [{"product_id": ARROZ_ID, "quantity": 2}]
    order = orders.create_order("any", items, shipping_address_id=ADDRESS_ID)
    assert order["status"] == "pending"
    assert order["shipping_address_id"] == ADDRESS_ID
    assert order["subtotal"] == "13000.00"
    assert order["total_amount"] == "13000.00"
    assert order["items"][0]["product_id"] == ARROZ_ID
    assert order["items"][0]["line_total"] == "13000.00"


def test_create_order_is_retrievable_afterwards():
    items = [{"product_id": ARROZ_ID, "quantity": 1}]
    order = orders.create_order("any", items, shipping_address_id=ADDRESS_ID)
    fetched = orders.get_order("any", order["id"])
    assert fetched is not None
    assert fetched["id"] == order["id"]


def test_create_order_unknown_product_raises_conflict():
    items = [{"product_id": "00000000-0000-0000-0000-000000000999", "quantity": 1}]
    with pytest.raises(ApiConflictError):
        orders.create_order("any", items, shipping_address_id=ADDRESS_ID)


def test_cancel_order_sets_status():
    # Cancel a freshly created order rather than mutating the seed fixtures
    # in mock_data.MOCK_ORDERS, which other tests also read.
    items = [{"product_id": ARROZ_ID, "quantity": 1}]
    order = orders.create_order("any", items, shipping_address_id=ADDRESS_ID)
    result = orders.cancel_order("any", order["id"])
    assert result["status"] == "cancelled"


def test_transitions_mirror_backend_table():
    """Mirror of backend-api's order_service._ALLOWED_TRANSITIONS: shipped
    and delivered are reached only through the shipment steps, never by a
    manual override.
    """
    assert orders.ORDER_TRANSITIONS == {
        "pending": ["cancelled"],
        "paid": ["preparing", "cancelled", "refunded"],
        "preparing": ["cancelled"],
        "shipped": [],
        "delivered": [],
        "cancelled": [],
        "refunded": [],
    }
    assert set(orders.ORDER_TRANSITIONS) == set(orders.ORDER_STATUSES)


def test_update_status_rejects_transition_outside_table():
    items = [{"product_id": ARROZ_ID, "quantity": 1}]
    order = orders.create_order("any", items, shipping_address_id=ADDRESS_ID)
    with pytest.raises(ApiConflictError):
        orders.update_status("any", order["id"], "shipped")
    assert order["status"] == "pending"
