from apps.core.templatetags.pagination import page_window


def test_short_list_shows_every_page():
    assert page_window(1, 5) == [1, 2, 3, 4, 5]


def test_long_list_elides_both_sides_of_the_current_page():
    assert page_window(50, 4925) == [1, None, 48, 49, 50, 51, 52, None, 4925]


def test_one_page_gap_shows_the_number_not_an_ellipsis():
    assert page_window(5, 20) == [1, 2, 3, 4, 5, 6, 7, None, 20]


def test_last_page():
    assert page_window(4925, 4925) == [1, None, 4923, 4924, 4925]


def test_duration_label_scales_minutes_hours_days_years():
    from apps.core.templatetags.money import duration_label, stock_gap

    assert [duration_label(s) for s in (90, 5400, 30 * 3600, 3 * 86400, 800 * 86400)] == [
        "1 min", "1 h 30 min", "30 h", "3 d", "2 años"
    ]
    assert [stock_gap(0, 10), stock_gap(7, 3), stock_gap(5, 5)] == ["−10", "+4", "0"]
