"""Template filters for formatting money and small display helpers.

The backend sends money as a decimal-as-string (see API_CONTRACT.md:
"All money fields are strings with 2 decimal places"). This filter formats
that string for display with thousands separators, matching how prices are
written in Colombia (period as thousands separator): $6.500 rather than
$6,500.00 or $6500.
"""

from decimal import Decimal, InvalidOperation

from django import template

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
