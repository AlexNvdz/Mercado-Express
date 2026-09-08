from services import mock_data, orders, payments


def test_create_payment_marks_order_paid():
    order = orders.create_order(
        "any",
        [{"product_id": mock_data.MOCK_PRODUCTS[0]["id"], "quantity": 1}],
        shipping_address_id=mock_data.MOCK_ADDRESSES[0]["id"],
    )
    payment = payments.create_payment("any", order["id"], method="card")
    assert payment["status"] == "completed"

    updated_order = orders.get_order("any", order["id"])
    assert updated_order["status"] == "paid"


def test_list_payments_for_order():
    order_id = mock_data.MOCK_ORDERS[0]["id"]
    result = payments.list_payments_for_order("any", order_id)
    assert len(result) >= 1
    assert result[0]["order_id"] == order_id


def test_list_payments_for_order_with_no_payments():
    assert payments.list_payments_for_order("any", "00000000-0000-0000-0000-000000000999") == []
