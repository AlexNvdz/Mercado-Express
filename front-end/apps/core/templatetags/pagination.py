"""Numbered pagination for every paginated list (`{% pagination page pages %}`).

Lists reach thousands of pages (about 4,900 for orders), so prev/next alone
is not enough: this shows the first and last page, two pages either side of
the current one and a "go to page" field. Links keep the other querystring
parameters (filters, search) through Django's `{% querystring %}`.
"""

from django import template

register = template.Library()


def page_window(page: int, pages: int, around: int = 2) -> list[int | None]:
    """Page numbers to show, with None where a gap of 2+ pages is elided."""
    shown = sorted({1, pages, *range(max(1, page - around), min(pages, page + around) + 1)})
    window: list[int | None] = []
    previous = 0
    for number in shown:
        if number - previous == 2:
            window.append(previous + 1)  # a one-page gap reads better as the number than as "…"
        elif number - previous > 2:
            window.append(None)
        window.append(number)
        previous = number
    return window


@register.inclusion_tag("partials/pagination.html", takes_context=True)
def pagination(context, page: int, pages: int):
    return {
        "request": context["request"],
        "page": page,
        "pages": pages,
        "window": page_window(page, pages) if pages > 1 else [],
    }
