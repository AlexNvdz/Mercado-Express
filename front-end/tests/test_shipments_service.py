from services import mock_data, shipments


def test_get_shipment_for_shipped_order():
    order_id = mock_data.MOCK_ORDERS[1]["id"]  # seeded as "shipped" in mock_data
    shipment = shipments.get_shipment_for_order("any", order_id)
    assert shipment is not None
    assert shipment["tracking_number"]


def test_get_shipment_for_order_without_shipment():
    assert shipments.get_shipment_for_order("any", "00000000-0000-0000-0000-000000000999") is None
