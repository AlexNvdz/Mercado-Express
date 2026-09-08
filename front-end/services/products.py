"""
Category/product catalog access. See ../API_CONTRACT.md:
    GET  /api/v1/categories                 ?page=&page_size=
    GET  /api/v1/categories/{category_id}
    GET  /api/v1/products                   ?category_id=&page=&page_size=
    GET  /api/v1/products/{product_id}

Both list endpoints are paginated (`{"items": [...], "total", "page",
"page_size", "pages"}`); the functions below return that envelope as-is so
callers can build pagination UI later. Ids are UUID strings, no slugs.

The contract has no product/category text-search param yet -- see
API_INTEGRATION_NOTES.md (ENDPOINT SOLICITADO). `search` here only filters
whatever page was already fetched; it is NOT a substitute for server-side
search over the full catalog.
"""

from __future__ import annotations

from django.conf import settings

from . import mock_data
from .api_client import api_client
from .exceptions import ApiNotFoundError


def list_categories(*, page: int = 1, page_size: int = 100) -> dict:
    if settings.API_USE_MOCKS:
        items = mock_data.MOCK_CATEGORIES
        return {"items": items, "total": len(items), "page": 1, "page_size": len(items), "pages": 1}

    return api_client.get(
        "/api/v1/categories", params={"page": page, "page_size": page_size}
    )


def get_category(category_id: str) -> dict | None:
    if settings.API_USE_MOCKS:
        return next((c for c in mock_data.MOCK_CATEGORIES if c["id"] == str(category_id)), None)

    try:
        return api_client.get(f"/api/v1/categories/{category_id}")
    except ApiNotFoundError:
        return None


def list_products(
    *, category_id: str | None = None, search: str | None = None, page: int = 1, page_size: int = 50
) -> dict:
    if settings.API_USE_MOCKS:
        items = mock_data.MOCK_PRODUCTS
        if category_id:
            items = [p for p in items if p["category_id"] == str(category_id)]
        if search:
            needle = search.lower()
            items = [p for p in items if needle in p["name"].lower()]
        return {"items": items, "total": len(items), "page": 1, "page_size": len(items), "pages": 1}

    params: dict = {"page": page, "page_size": page_size}
    if category_id:
        params["category_id"] = category_id
    result = api_client.get("/api/v1/products", params=params)
    if search:
        needle = search.lower()
        result = {**result, "items": [p for p in result["items"] if needle in p["name"].lower()]}
    return result


def get_product(product_id: str) -> dict | None:
    if settings.API_USE_MOCKS:
        return next((p for p in mock_data.MOCK_PRODUCTS if p["id"] == str(product_id)), None)

    try:
        return api_client.get(f"/api/v1/products/{product_id}")
    except ApiNotFoundError:
        return None
