"""Template filters for formatting money and small display helpers.

The backend sends money as a decimal-as-string (see API_CONTRACT.md:
"All money fields are strings with 2 decimal places"). This filter formats
that string for display with thousands separators, matching how prices are
written in Colombia (period as thousands separator): $6.500 rather than
$6,500.00 or $6500.
"""

from datetime import UTC
from decimal import Decimal, InvalidOperation

from django import template
from django.utils import timezone
from django.utils.dateparse import parse_datetime

register = template.Library()


@register.filter(name="money")
def money(value):
    """"6500.00" -> "6.500". Falls back to the raw value if it can't parse."""
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError):
        return value
    whole = int(amount.to_integral_value(rounding="ROUND_HALF_UP"))
    return f"{whole:,}".replace(",", ".")


def _parse_api_datetime(value):
    try:
        parsed = parse_datetime(str(value))
    except ValueError:
        return None
    if parsed is not None and timezone.is_naive(parsed):
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


@register.filter(name="since")
def since(value):
    """ISO 8601 UTC timestamp -> time elapsed until now: "45 min", "26 h", "3 d"."""
    parsed = _parse_api_datetime(value)
    if parsed is None:
        return ""
    return duration_label((timezone.now() - parsed).total_seconds())


@register.filter(name="hours_since")
def hours_since(value):
    """Whole hours elapsed since an ISO 8601 UTC timestamp (0 if unparseable)."""
    parsed = _parse_api_datetime(value)
    return int((timezone.now() - parsed).total_seconds() // 3600) if parsed else 0


@register.filter(name="stock_gap")
def stock_gap(available, reorder_level):
    """Signed distance from the reorder level, typeset like a bulletin
    variation: "−10", "+4", "0" (a real minus sign, not a hyphen).
    """
    try:
        gap = int(available) - int(reorder_level)
    except (TypeError, ValueError):
        return ""
    if gap < 0:
        return f"−{-gap}"
    return f"+{gap}" if gap else "0"


@register.filter(name="stock_gap_tone")
def stock_gap_tone(available, reorder_level):
    """CSS modifier for a stock variation, following the sign of stock_gap:
    below the reorder level points down, at it is flat, above it points up.
    """
    try:
        gap = int(available) - int(reorder_level)
    except (TypeError, ValueError):
        return "var--flat"
    return "var--down" if gap < 0 else "var--up" if gap > 0 else "var--flat"


def duration_label(seconds: float) -> str:
    minutes = max(0, int(seconds // 60))
    if minutes < 60:
        return f"{minutes} min"
    if minutes < 48 * 60:
        hours, rest = divmod(minutes, 60)
        return f"{hours} h {rest} min" if hours < 10 and rest else f"{hours} h"
    days = minutes // (24 * 60)
    if days < 365:
        return f"{days} d"
    years = days // 365
    return f"{years} año{'s' if years > 1 else ''}"


def _format_local(value, fmt):
    """Parse an ISO 8601 UTC timestamp from the API and format it in the
    site's TIME_ZONE. Falls back to the raw value if it can't parse.
    """
    parsed = _parse_api_datetime(value)
    if parsed is None:
        return value
    return timezone.localtime(parsed).strftime(fmt)


@register.filter(name="api_datetime")
def api_datetime(value):
    """ISO 8601 UTC timestamp -> "07/10/2026 09:00" in the site's TIME_ZONE."""
    return _format_local(value, "%d/%m/%Y %H:%M")


@register.filter(name="api_date")
def api_date(value):
    """ISO 8601 UTC timestamp -> "07/10/2026" in the site's TIME_ZONE, so a
    late-evening order isn't shown with tomorrow's UTC date.
    """
    return _format_local(value, "%d/%m/%Y")
