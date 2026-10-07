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


def test_list_orders_filters_by_status_in_mock_mode():
    result = orders.list_orders("any", status="shipped")
    assert [o["status"] for o in result["items"]] == ["shipped"]
    assert result["total"] == 1


def test_list_orders_sends_status_param(api_calls):
    orders.list_orders("tok", page=2, page_size=20, status="paid")
    method, path, kwargs = api_calls[0]
    assert (method, path) == ("GET", "/api/v1/orders")
    assert kwargs["params"] == {"page": 2, "page_size": 20, "status": "paid"}


def test_list_orders_without_status_sends_no_status_param(api_calls):
    orders.list_orders("tok")
    assert "status" not in api_calls[0][2]["params"]


def test_status_history_mock_is_oldest_first():
    history = orders.get_status_history("any", mock_data.MOCK_ORDERS[0]["id"])
    assert history[0]["source"] == "order_created"
    assert history[0]["from_status"] is None
    assert history[-1]["to_status"] == "delivered"


def test_status_history_empty_for_order_without_entries():
    assert orders.get_status_history("any", "00000000-0000-0000-0000-000000000999") == []


def test_status_history_request(api_calls):
    api_calls.response = []
    orders.get_status_history("tok", "order-1")
    method, path, kwargs = api_calls[0]
    assert (method, path) == ("GET", "/api/v1/orders/order-1/history")
    assert kwargs["token"] == "tok"


def test_every_history_source_has_a_label():
    sources = {e["source"] for entries in mock_data.MOCK_ORDER_HISTORY.values() for e in entries}
    assert sources <= set(orders.ORDER_STATUS_SOURCE_LABELS)
    assert len(orders.ORDER_STATUS_SOURCE_LABELS) == 7
