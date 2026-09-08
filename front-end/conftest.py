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
    """services/orders.py, services/payments.py and services/customers.py
    mutate the module-level mock_data lists/dicts in mock mode (mimicking
    real persistence) so a just-created order/address or an updated profile
    can be read back in the same test. Snapshot/restore them per test so
    that mutation doesn't leak between tests.
    """
    orders_snapshot = copy.deepcopy(mock_data.MOCK_ORDERS)
    payments_snapshot = copy.deepcopy(mock_data.MOCK_PAYMENTS)
    user_snapshot = copy.deepcopy(mock_data.MOCK_USER)
    addresses_snapshot = copy.deepcopy(mock_data.MOCK_ADDRESSES)
    yield
    mock_data.MOCK_ORDERS[:] = orders_snapshot
    mock_data.MOCK_PAYMENTS.clear()
    mock_data.MOCK_PAYMENTS.update(payments_snapshot)
    mock_data.MOCK_USER.clear()
    mock_data.MOCK_USER.update(user_snapshot)
    mock_data.MOCK_ADDRESSES[:] = addresses_snapshot
