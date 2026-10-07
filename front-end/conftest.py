"""Project-wide pytest fixtures.

The real backend contract (API_CONTRACT.md) requires a live FastAPI +
PostgreSQL to exercise end to end. This project's test suite instead runs
against services/mock_data.py so it stays fast and hermetic regardless of
what .env sets locally -- the actual HTTP-calling code path is exercised
separately in tests/test_api_client.py with httpx mocked.
"""

import copy

import pytest

from services import mock_data


@pytest.fixture(autouse=True)
def _force_mock_backend(settings):
    settings.API_USE_MOCKS = True


@pytest.fixture(autouse=True)
def _reset_mock_data():
    """services/orders.py, services/payments.py, services/customers.py,
    services/products.py and services/inventory.py mutate the module-level
    mock_data lists/dicts in mock mode (mimicking real persistence) so a
    just-created order/address/product/category or an adjusted stock level
    can be read back in the same test. Snapshot/restore them per test so
    that mutation doesn't leak between tests.
    """
    orders_snapshot = copy.deepcopy(mock_data.MOCK_ORDERS)
    payments_snapshot = copy.deepcopy(mock_data.MOCK_PAYMENTS)
    user_snapshot = copy.deepcopy(mock_data.MOCK_USER)
    addresses_snapshot = copy.deepcopy(mock_data.MOCK_ADDRESSES)
    products_snapshot = copy.deepcopy(mock_data.MOCK_PRODUCTS)
    categories_snapshot = copy.deepcopy(mock_data.MOCK_CATEGORIES)
    inventory_snapshot = copy.deepcopy(mock_data.MOCK_INVENTORY)
    shipments_snapshot = copy.deepcopy(mock_data.MOCK_SHIPMENTS)
    report_summary_snapshot = copy.deepcopy(mock_data.MOCK_REPORT_SUMMARY)
    order_history_snapshot = copy.deepcopy(mock_data.MOCK_ORDER_HISTORY)
    inventory_history_snapshot = copy.deepcopy(mock_data.MOCK_INVENTORY_HISTORY)
    yield
    mock_data.MOCK_ORDERS[:] = orders_snapshot
    mock_data.MOCK_PAYMENTS.clear()
    mock_data.MOCK_PAYMENTS.update(payments_snapshot)
    mock_data.MOCK_USER.clear()
    mock_data.MOCK_USER.update(user_snapshot)
    mock_data.MOCK_ADDRESSES[:] = addresses_snapshot
    mock_data.MOCK_PRODUCTS[:] = products_snapshot
    mock_data.MOCK_CATEGORIES[:] = categories_snapshot
    mock_data.MOCK_INVENTORY.clear()
    mock_data.MOCK_INVENTORY.update(inventory_snapshot)
    mock_data.MOCK_SHIPMENTS.clear()
    mock_data.MOCK_SHIPMENTS.update(shipments_snapshot)
    mock_data.MOCK_REPORT_SUMMARY.clear()
    mock_data.MOCK_REPORT_SUMMARY.update(report_summary_snapshot)
    mock_data.MOCK_ORDER_HISTORY.clear()
    mock_data.MOCK_ORDER_HISTORY.update(order_history_snapshot)
    mock_data.MOCK_INVENTORY_HISTORY.clear()
    mock_data.MOCK_INVENTORY_HISTORY.update(inventory_history_snapshot)


@pytest.fixture
def api_calls(settings, monkeypatch):
    """Opt-in: switch one test to the real-API code path with the HTTP layer
    stubbed out, to check which method/path/body a service sends. Each call
    is recorded as `(method, path, kwargs)` and returns `api_calls.response`
    (default `{}`); set it to a callable `(method, path, kwargs) -> body` to
    answer per path/params.
    """
    settings.API_USE_MOCKS = False
    calls = _RecordedCalls()
    calls.response = {}

    def fake_request(self, method, path, **kwargs):
        calls.append((method, path, kwargs))
        if callable(calls.response):
            return calls.response(method, path, kwargs)
        return calls.response

    monkeypatch.setattr("services.api_client.ApiClient.request", fake_request)
    return calls


class _RecordedCalls(list):
    response: object
