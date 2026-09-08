"""
Category/product catalog access. See ../API_CONTRACT.md:
    GET  /api/v1/categories                 ?page=&page_size=
    GET  /api/v1/categories/{category_id}
    GET  /api/v1/products                   ?category_id=&search=&page=&page_size=
    GET  /api/v1/products/{product_id}

Both list endpoints are paginated (`{"items": [...], "total", "page",
"page_size", "pages"}`); the functions below return that envelope as-is so
callers can build pagination UI.  Ids are UUID strings, no slugs.

`search` (case-insensitive match on name or SKU) was added by backend-api in
response to the ENDPOINT SOLICITADO in API_INTEGRATION_NOTES.md -- confirmed
in ../backend-api/app/services/product_service.py; not documented in
API_CONTRACT.md yet, ask the backend to add it there.
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
    *, category_id: str | None = None, search: str | None = None, page: int = 1, page_size: int = 24
) -> dict:
    if settings.API_USE_MOCKS:
        items = mock_data.MOCK_PRODUCTS
        if category_id:
            items = [p for p in items if p["category_id"] == str(category_id)]
        if search:
            needle = search.lower()
            items = [p for p in items if needle in p["name"].lower() or needle in p["sku"].lower()]
        return {"items": items, "total": len(items), "page": 1, "page_size": len(items) or 1, "pages": 1}

    params: dict = {"page": page, "page_size": page_size}
    if category_id:
        params["category_id"] = category_id
    if search:
        params["search"] = search
    return api_client.get("/api/v1/products", params=params)


def get_product(product_id: str) -> dict | None:
    if settings.API_USE_MOCKS:
        return next((p for p in mock_data.MOCK_PRODUCTS if p["id"] == str(product_id)), None)

    try:
        return api_client.get(f"/api/v1/products/{product_id}")
    except ApiNotFoundError:
        return None
