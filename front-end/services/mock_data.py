"""
Mock data used when settings.API_USE_MOCKS is True.

Shapes here mirror ../API_CONTRACT.md as closely as possible (UUID string
ids, decimal-as-string money fields, ISO 8601 UTC timestamps) so that
switching a service function from mock to real API call is a drop-in change.

This module is used for:
  - this project's own test suite (see conftest.py: API_USE_MOCKS is forced
    True for every test, regardless of .env, so tests never need a live
    backend)
  - optional offline UI work if a developer sets API_USE_MOCKS=True locally

It must NEVER be imported by views/templates directly -- only by the
services/*.py modules, gated behind `if settings.API_USE_MOCKS`.
"""

from __future__ import annotations

MOCK_CATEGORIES = [
    {"id": "00000000-0000-0000-0000-000000000101", "name": "Abarrotes", "description": "Arroz, granos, aceites y más.", "parent_id": None, "is_active": True},
    {"id": "00000000-0000-0000-0000-000000000102", "name": "Frutas y verduras", "description": "Productos frescos.", "parent_id": None, "is_active": True},
    {"id": "00000000-0000-0000-0000-000000000103", "name": "Lácteos", "description": "Leche, quesos y derivados.", "parent_id": None, "is_active": True},
    {"id": "00000000-0000-0000-0000-000000000104", "name": "Limpieza", "description": "Productos de aseo del hogar.", "parent_id": None, "is_active": True},
]

MOCK_PRODUCTS = [
    {
        "id": "00000000-0000-0000-0000-000000000201",
        "sku": "SKU-ARR-001",
        "name": "Arroz blanco 1kg",
        "description": "Arroz blanco de grano largo, bolsa de 1kg.",
        "category_id": "00000000-0000-0000-0000-000000000101",
        "price": "6500.00",
        "is_active": True,
    },
    {
        "id": "00000000-0000-0000-0000-000000000202",
        "sku": "SKU-ACE-001",
        "name": "Aceite vegetal 1L",
        "description": "Aceite vegetal comestible, botella de 1 litro.",
        "category_id": "00000000-0000-0000-0000-000000000101",
        "price": "12900.00",
        "is_active": True,
    },
    {
        "id": "00000000-0000-0000-0000-000000000203",
        "sku": "SKU-LEN-001",
        "name": "Lentejas 500g",
        "description": "Lentejas secas, bolsa de 500g.",
        "category_id": "00000000-0000-0000-0000-000000000101",
        "price": "4200.00",
        "is_active": True,
    },
    {
        "id": "00000000-0000-0000-0000-000000000204",
        "sku": "SKU-BAN-001",
        "name": "Banano (kg)",
        "description": "Banano fresco, precio por kilogramo.",
        "category_id": "00000000-0000-0000-0000-000000000102",
        "price": "3200.00",
        "is_active": True,
    },
    {
        "id": "00000000-0000-0000-0000-000000000205",
        "sku": "SKU-TOM-001",
        "name": "Tomate (kg)",
        "description": "Tomate chonto fresco, precio por kilogramo.",
        "category_id": "00000000-0000-0000-0000-000000000102",
        "price": "3800.00",
        "is_active": True,
    },
    {
        "id": "00000000-0000-0000-0000-000000000206",
        "sku": "SKU-LEC-001",
        "name": "Leche entera 1L",
        "description": "Leche entera pasteurizada, cartón de 1 litro.",
        "category_id": "00000000-0000-0000-0000-000000000103",
        "price": "4500.00",
        "is_active": True,
    },
    {
        "id": "00000000-0000-0000-0000-000000000207",
        "sku": "SKU-QUE-001",
        "name": "Queso campesino 250g",
        "description": "Queso campesino fresco, bloque de 250g.",
        "category_id": "00000000-0000-0000-0000-000000000103",
        "price": "8900.00",
        "is_active": True,
    },
    {
        "id": "00000000-0000-0000-0000-000000000208",
        "sku": "SKU-DET-001",
        "name": "Detergente en polvo 1kg",
        "description": "Detergente en polvo para ropa, bolsa de 1kg.",
        "category_id": "00000000-0000-0000-0000-000000000104",
        "price": "9900.00",
        "is_active": True,
    },
]

# Keyed by product_id -- mirrors GET /api/v1/inventory/{product_id}.
MOCK_INVENTORY = {
    "00000000-0000-0000-0000-000000000201": {"quantity_on_hand": 120, "quantity_reserved": 0},
    "00000000-0000-0000-0000-000000000202": {"quantity_on_hand": 80, "quantity_reserved": 0},
    "00000000-0000-0000-0000-000000000203": {"quantity_on_hand": 60, "quantity_reserved": 0},
    "00000000-0000-0000-0000-000000000204": {"quantity_on_hand": 200, "quantity_reserved": 0},
    "00000000-0000-0000-0000-000000000205": {"quantity_on_hand": 150, "quantity_reserved": 0},
    "00000000-0000-0000-0000-000000000206": {"quantity_on_hand": 90, "quantity_reserved": 0},
    "00000000-0000-0000-0000-000000000207": {"quantity_on_hand": 40, "quantity_reserved": 0},
    "00000000-0000-0000-0000-000000000208": {"quantity_on_hand": 0, "quantity_reserved": 0},
}

MOCK_USER = {
    "id": "00000000-0000-0000-0000-000000000501",
    "email": "cliente.demo@mercadoexpress.test",
    "full_name": "Cliente Demo",
    "phone": "+57 300 000 0000",
    "role": "customer",
    "is_active": True,
}

MOCK_ADDRESSES = [
    {
        "id": "00000000-0000-0000-0000-000000000601",
        "line1": "Calle 10 # 20-30",
        "line2": None,
        "city": "Bogotá",
        "state": "Bogotá D.C.",
        "postal_code": "110111",
        "country": "CO",
        "is_default": True,
    },
]

MOCK_ORDERS = [
    {
        "id": "00000000-0000-0000-0000-000000000701",
        "order_number": "ORD-DEMO0001",
        "customer_id": MOCK_USER["id"],
        "status": "delivered",
        "subtotal": "17700.00",
        "tax_amount": "0.00",
        "shipping_amount": "0.00",
        "total_amount": "17700.00",
        "shipping_address_id": MOCK_ADDRESSES[0]["id"],
        "notes": None,
        "items": [
            {"id": "i1", "product_id": "00000000-0000-0000-0000-000000000201", "product_name": "Arroz blanco 1kg", "quantity": 2, "unit_price": "6500.00", "line_total": "13000.00"},
            {"id": "i2", "product_id": "00000000-0000-0000-0000-000000000206", "product_name": "Leche entera 1L", "quantity": 1, "unit_price": "4500.00", "line_total": "4500.00"},
        ],
        "created_at": "2026-08-20T14:30:00Z",
        "updated_at": "2026-08-21T10:15:00Z",
    },
    {
        "id": "00000000-0000-0000-0000-000000000702",
        "order_number": "ORD-DEMO0002",
        "customer_id": MOCK_USER["id"],
        "status": "shipped",
        "subtotal": "12900.00",
        "tax_amount": "0.00",
        "shipping_amount": "0.00",
        "total_amount": "12900.00",
        "shipping_address_id": MOCK_ADDRESSES[0]["id"],
        "notes": None,
        "items": [
            {"id": "i3", "product_id": "00000000-0000-0000-0000-000000000202", "product_name": "Aceite vegetal 1L", "quantity": 1, "unit_price": "12900.00", "line_total": "12900.00"},
        ],
        "created_at": "2026-09-05T09:10:00Z",
        "updated_at": "2026-09-06T08:00:00Z",
    },
]

# Keyed by order_id -- mirrors GET /api/v1/shipments/order/{order_id}.
# NOTE: the response shape for this endpoint isn't shown in API_CONTRACT.md
# (only the POST request body is) -- see ENDPOINT SOLICITADO in
# API_INTEGRATION_NOTES.md asking the backend to confirm/document it.
MOCK_SHIPMENTS = {
    "00000000-0000-0000-0000-000000000701": {
        "id": "ship-1", "order_id": "00000000-0000-0000-0000-000000000701",
        "carrier": "manual", "tracking_number": "MANUAL-0000000001",
        "status": "delivered",
        "shipped_at": "2026-08-20T18:00:00Z",
        "delivered_at": "2026-08-21T10:15:00Z",
    },
    "00000000-0000-0000-0000-000000000702": {
        "id": "ship-2", "order_id": "00000000-0000-0000-0000-000000000702",
        "carrier": "manual", "tracking_number": "MANUAL-0000000002",
        "status": "shipped",
        "shipped_at": "2026-09-06T08:00:00Z",
        "delivered_at": None,
    },
}

# Keyed by order_id -- mirrors GET /api/v1/payments/order/{order_id}.
MOCK_PAYMENTS = {
    "00000000-0000-0000-0000-000000000701": [
        {"id": "pay-1", "order_id": "00000000-0000-0000-0000-000000000701", "amount": "17700.00", "currency": "USD", "status": "completed", "provider": "manual", "method": "card", "paid_at": "2026-08-20T14:35:00Z"},
    ],
    "00000000-0000-0000-0000-000000000702": [
        {"id": "pay-2", "order_id": "00000000-0000-0000-0000-000000000702", "amount": "12900.00", "currency": "USD", "status": "completed", "provider": "manual", "method": "card", "paid_at": "2026-09-05T09:20:00Z"},
    ],
}
