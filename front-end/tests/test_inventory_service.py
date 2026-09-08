from services import mock_data, inventory

ARROZ_ID = mock_data.MOCK_PRODUCTS[0]["id"]
DETERGENTE_ID = mock_data.MOCK_PRODUCTS[-1]["id"]  # zero stock in mock data


def test_get_availability_found():
    record = inventory.get_availability(ARROZ_ID)
    assert record is not None
    assert record["quantity_available"] == record["quantity_on_hand"] - record["quantity_reserved"]


def test_get_availability_zero_stock():
    record = inventory.get_availability(DETERGENTE_ID)
    assert record["quantity_available"] == 0


def test_get_availability_unknown_product():
    assert inventory.get_availability("00000000-0000-0000-0000-000000000999") is None
