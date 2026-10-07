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


def test_list_inventory_low_stock_filters_by_reorder_level():
    page = inventory.list_inventory("any", low_stock=True)
    assert [row["product_id"] for row in page["items"]] == [DETERGENTE_ID]
    assert page["total"] == 1


def test_list_inventory_without_filter_returns_every_row():
    page = inventory.list_inventory("any")
    assert page["total"] == len(mock_data.MOCK_INVENTORY)


def test_list_inventory_sends_low_stock_flag(api_calls):
    inventory.list_inventory("tok", low_stock=True, page_size=100)
    method, path, kwargs = api_calls[0]
    assert (method, path) == ("GET", "/api/v1/inventory")
    assert kwargs["params"] == {"page": 1, "page_size": 100, "low_stock": "true"}
    assert kwargs["token"] == "tok"


def _page(items, page, pages):
    return {"items": items, "total": len(items), "page": page, "page_size": 100, "pages": pages}


def _row(product_id):
    return {"product_id": product_id, "quantity_on_hand": 5, "quantity_reserved": 0, "quantity_available": 5, "reorder_level": 1}


def test_availability_by_product_mock_skips_products_without_row():
    result = inventory.availability_by_product("any", [ARROZ_ID, "00000000-0000-0000-0000-000000000999"])
    assert set(result) == {ARROZ_ID}


def test_availability_by_product_stops_once_all_found(api_calls):
    pages = {1: _page([_row("a"), _row("x")], 1, 3), 2: _page([_row("b")], 2, 3), 3: _page([_row("c")], 3, 3)}
    api_calls.response = lambda method, path, kwargs: pages[kwargs["params"]["page"]]

    result = inventory.availability_by_product("tok", ["a", "b"])

    assert set(result) == {"a", "b"}
    assert [kwargs["params"]["page"] for _, _, kwargs in api_calls] == [1, 2]
    assert all(kwargs["params"]["page_size"] == inventory.MAX_PAGE_SIZE for _, _, kwargs in api_calls)


def test_availability_by_product_reads_every_page_when_a_row_is_missing(api_calls):
    pages = {1: _page([_row("a")], 1, 2), 2: _page([_row("b")], 2, 2)}
    api_calls.response = lambda method, path, kwargs: pages[kwargs["params"]["page"]]

    result = inventory.availability_by_product("tok", ["a", "missing"])

    assert set(result) == {"a"}
    assert len(api_calls) == 2


def test_availability_by_product_with_no_inventory_rows(api_calls):
    api_calls.response = {"items": [], "total": 0, "page": 1, "page_size": 100, "pages": 0}
    assert inventory.availability_by_product("tok", ["a"]) == {}
    assert len(api_calls) == 1


def test_availability_by_product_without_products_makes_no_request(api_calls):
    assert inventory.availability_by_product("tok", []) == {}
    assert api_calls == []


def test_list_inventory_skips_inactive_products_unless_asked():
    mock_data.MOCK_PRODUCTS[-1]["is_active"] = False  # the low-stock detergent
    assert inventory.list_inventory("any", low_stock=True)["total"] == 0
    assert inventory.list_inventory("any", low_stock=True, include_inactive=True)["total"] == 1


def test_availability_by_product_includes_inactive_rows(api_calls):
    api_calls.response = _page([_row("a")], 1, 1)
    inventory.availability_by_product("tok", ["a"])
    assert api_calls[0][2]["params"]["include_inactive"] == "true"


def test_set_levels_sends_reason(api_calls):
    inventory.set_levels("tok", ARROZ_ID, 50, 10, reason="Inventario anual")
    method, path, kwargs = api_calls[0]
    assert (method, path) == ("PUT", f"/api/v1/inventory/{ARROZ_ID}")
    assert kwargs["json"] == {"quantity_on_hand": 50, "reorder_level": 10, "reason": "Inventario anual"}


def test_mock_adjust_records_history_newest_first():
    inventory.adjust_stock("any", ARROZ_ID, 5, "Primero")
    inventory.set_levels("any", ARROZ_ID, 100, 25, reason="Segundo")
    entries = inventory.list_history("any", ARROZ_ID)["items"]
    assert [e["reason"] for e in entries] == ["Segundo", "Primero"]
    assert entries[1]["quantity_delta"] == 5
    assert entries[0]["kind"] == "set_levels"
    assert entries[0]["reorder_level_after"] == 25


def test_list_history_request(api_calls):
    inventory.list_history("tok", ARROZ_ID, page=3, page_size=20)
    method, path, kwargs = api_calls[0]
    assert (method, path) == ("GET", f"/api/v1/inventory/{ARROZ_ID}/history")
    assert kwargs["params"] == {"page": 3, "page_size": 20}
    assert kwargs["token"] == "tok"
