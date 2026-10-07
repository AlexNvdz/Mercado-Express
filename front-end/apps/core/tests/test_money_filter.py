from apps.core.templatetags.money import api_datetime


def test_api_datetime_converts_utc_to_site_time_zone():
    # America/Bogota is UTC-5 (see config/settings/base.py TIME_ZONE).
    assert api_datetime("2026-08-21T10:15:00Z") == "21/08/2026 05:15"


def test_api_datetime_handles_microseconds_and_offsets():
    assert api_datetime("2026-09-08T11:06:19.263086+00:00") == "08/09/2026 06:06"


def test_api_datetime_returns_unparseable_value_as_is():
    assert api_datetime("not a date") == "not a date"
    assert api_datetime(None) is None
