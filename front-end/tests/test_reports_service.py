from decimal import Decimal

from services import mock_data, reports


def test_dashboard_stats_come_from_summary():
    stats = reports.get_dashboard_stats("any")
    summary = mock_data.MOCK_REPORT_SUMMARY

    assert stats["net_revenue"] == Decimal(summary["net_revenue"])
    assert stats["gross_revenue"] == Decimal(summary["gross_revenue"])
    assert stats["refunded_amount"] == Decimal(summary["refunded_amount"])
    assert stats["sale_count"] == summary["sale_count"]
    assert stats["reversal_count"] == summary["reversal_count"]
    assert stats["total_customers"] == summary["customer_count"]
    assert stats["total_products"] == summary["product_count"]
    assert stats["top_products"][0]["units_sold"] == 2


def test_orders_by_status_follows_lifecycle_and_hides_zero_rows():
    stats = reports.get_dashboard_stats("any")
    assert list(stats["orders_by_status"]) == ["shipped", "delivered"]
    assert stats["total_orders"] == 2


def test_low_stock_rows_carry_product_names():
    stats = reports.get_dashboard_stats("any")
    assert stats["low_stock_count"] == 1
    row = stats["low_stock"][0]
    assert row["name"] == "Detergente en polvo 1kg"
    assert row["availability"]["quantity_available"] == 0


def test_summary_request(api_calls):
    reports.get_summary("tok", top_products_limit=6)
    method, path, kwargs = api_calls[0]
    assert (method, path) == ("GET", "/api/v1/reports/summary")
    assert kwargs["params"] == {"top_products_limit": 6}
    assert kwargs["token"] == "tok"


def test_low_stock_ignores_inactive_products():
    mock_data.MOCK_PRODUCTS[-1]["is_active"] = False  # the low-stock detergent
    stats = reports.get_dashboard_stats("any")
    assert stats["low_stock_count"] == 0
