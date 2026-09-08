# MercadoExpress — API Contract (Backend for Django frontend)

Owner: `backend-api` (FastAPI). Consumer: `front-end` (Django). This document
is the source of truth for how Django talks to the backend. It is updated by
the backend whenever an endpoint changes; the frontend should not need to
read backend source code to integrate.

**Do not connect Django directly to PostgreSQL for business data.** All
reads/writes of Customers, Products, Inventory, Orders, Payments, Shipments
and Sales go through this HTTP API.

## Base URL

| Environment | URL |
|---|---|
| Local dev (backend run with `uv run uvicorn`) | `http://localhost:8000` |
| Local dev (backend run with Docker Compose) | `http://localhost:8000` |
| Docker network (Django container calling API container) | `http://api:8000` (once both are wired into one compose project) |

All endpoints below are relative to this base URL and prefixed `/api/v1`.

Interactive docs (Swagger UI): `GET /docs`. OpenAPI schema: `GET /openapi.json`.
Health check (no auth): `GET /health`.

## Authentication

JWT bearer tokens, OAuth2-password-compatible login.

1. `POST /api/v1/auth/register` — self-service, always creates a `customer`.
   Staff/admin accounts are **not** self-service (no public "become admin"
   endpoint) — provisioned via a backend-side seed script
   (`uv run python -m app.scripts.seed_admin`, idempotent, runs
   automatically on every backend startup in Docker Compose). Ask the
   backend owner for admin credentials for your environment rather than
   trying to create one through the API.
2. `POST /api/v1/auth/login` — **form-encoded** (`application/x-www-form-urlencoded`),
   fields `username` (= email) and `password`. Returns an access token
   (short-lived, 30 min default) and a refresh token (7 days default).
3. `POST /api/v1/auth/refresh` — JSON `{"refresh_token": "..."}` → new access token.
4. Send `Authorization: Bearer <access_token>` on every authenticated request.

Roles: `customer`, `employee`, `admin`. Endpoints marked **staff** below
require `employee` or `admin` — see
`app/dependencies.py::require_staff`). Endpoints with no role note are
either public or require any authenticated user (noted per-endpoint).

### Example: register + login

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "jane@example.com",
  "password": "S3curePass!",
  "full_name": "Jane Doe",
  "phone": "+1-555-0100"
}
```
→ `201 Created`
```json
{
  "id": "b3f2b6f0-1234-4a5b-9c1d-abcdef123456",
  "email": "jane@example.com",
  "full_name": "Jane Doe",
  "phone": "+1-555-0100",
  "role": "customer",
  "is_active": true
}
```

```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=jane%40example.com&password=S3curePass!
```
→ `200 OK`
```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "token_type": "bearer"
}
```

## Error format

Every error response is:
```json
{ "detail": "Human-readable message." }
```
Standard status codes: `401` (missing/invalid/expired token), `403` (role not
permitted), `404` (not found / not yours), `409` (conflict — duplicate
unique field, insufficient stock, invalid status transition), `422`
(request body failed validation — Pydantic's default FastAPI error shape,
`{"detail": [...]}` with field-level errors).

## Pagination

List endpoints accept `page` (default 1) and `page_size` (default 20, max
100) query params and return:
```json
{ "items": [...], "total": 137, "page": 1, "page_size": 20, "pages": 7 }
```

---

## `/api/v1/auth`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | none | Register a new customer. |
| POST | `/auth/login` | none | Form login, returns token pair. |
| POST | `/auth/refresh` | none | Exchange refresh token for new access token. |
| GET | `/auth/me` | any user | Current user's profile. |

## `/api/v1/customers`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/customers/me` | any user | Own profile. |
| PATCH | `/customers/me` | any user | Update own `full_name` / `phone`. |
| GET | `/customers/me/addresses` | any user | List own addresses. |
| POST | `/customers/me/addresses` | any user | Add an address. |
| PATCH | `/customers/me/addresses/{address_id}` | any user | Update own address. |
| DELETE | `/customers/me/addresses/{address_id}` | any user | Delete own address. |
| GET | `/customers` | staff | Paginated list of customers. |
| GET | `/customers/{customer_id}` | staff | Get one customer. |

Address body:
```json
{
  "line1": "123 Main St",
  "line2": null,
  "city": "Springfield",
  "state": "IL",
  "postal_code": "62704",
  "country": "US",
  "is_default": true
}
```

## `/api/v1/categories`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/categories` | staff | Create category (optionally `parent_id` for subcategories). |
| GET | `/categories` | none | Paginated list. |
| GET | `/categories/{category_id}` | none | Get one. |
| PATCH | `/categories/{category_id}` | staff | Partial update. |
| DELETE | `/categories/{category_id}` | staff | Delete. |

```json
{ "name": "Electronics", "description": "Gadgets and devices", "parent_id": null, "is_active": true }
```

## `/api/v1/products`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/products` | staff | Create product (also creates its zero-stock inventory row). |
| GET | `/products?category_id=&search=&page=&page_size=` | none | Paginated list, optionally filtered by category and/or full-text-ish search. Only active products. |
| GET | `/products/{product_id}` | none | Get one. |
| PATCH | `/products/{product_id}` | staff | Partial update. |
| DELETE | `/products/{product_id}` | staff | Delete. |

```json
{
  "sku": "SKU-001",
  "name": "Wireless Mouse",
  "description": "2.4GHz wireless mouse",
  "category_id": "b3f2b6f0-1234-4a5b-9c1d-abcdef123456",
  "price": "19.99",
  "is_active": true
}
```
`price` is a decimal-as-string in responses (2 decimal places).

## `/api/v1/inventory`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/inventory/{product_id}` | none | Check availability. |
| POST | `/inventory/{product_id}/adjust` | staff | Add/remove stock by a signed delta. |
| PUT | `/inventory/{product_id}` | staff | Set absolute `quantity_on_hand` / `reorder_level`. |

```json
// GET response
{
  "id": "...", "product_id": "...",
  "quantity_on_hand": 50, "quantity_reserved": 3, "quantity_available": 47,
  "reorder_level": 10, "updated_at": "2026-09-08T10:00:00Z"
}
```
`quantity_available = quantity_on_hand - quantity_reserved`. Reservations are
made automatically when an order is created and released on cancellation.

## `/api/v1/orders`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/orders` | customer | Create an order: validates products, reserves stock, computes totals. |
| GET | `/orders?page=&page_size=` | any user | Customers see only their own orders; staff see all. |
| GET | `/orders/{order_id}` | any user | Get one (customers: only their own, else `404`). |
| POST | `/orders/{order_id}/cancel` | any user | Cancel (only while `pending`/`awaiting_payment`); releases reserved stock. |
| PATCH | `/orders/{order_id}/status` | staff | Force a status transition directly. |

Order status lifecycle: `pending → awaiting_payment → paid → preparing → shipped → delivered`,
with `cancelled` reachable from `pending`/`awaiting_payment`/`paid`/`preparing`,
and `refunded` reachable from `paid`. Invalid transitions return `409`.

```json
// POST /orders request
{
  "items": [
    { "product_id": "b3f2b6f0-...", "quantity": 2 }
  ],
  "shipping_address_id": "c4a1...",
  "notes": "Leave at front door"
}
```
```json
// response (201)
{
  "id": "...", "order_number": "ORD-A1B2C3D4E5",
  "customer_id": "...", "status": "pending",
  "subtotal": "39.98", "tax_amount": "0.00", "shipping_amount": "0.00", "total_amount": "39.98",
  "shipping_address_id": "c4a1...", "notes": "Leave at front door",
  "items": [
    { "id": "...", "product_id": "b3f2b6f0-...", "quantity": 2, "unit_price": "19.99", "line_total": "39.98" }
  ],
  "created_at": "2026-09-08T10:00:00Z", "updated_at": "2026-09-08T10:00:00Z"
}
```
`409` if any item is out of stock — no partial reservation is made (all-or-nothing).

## `/api/v1/payments`

No real payment gateway is integrated yet — `POST /payments` completes the
payment immediately via a manual/placeholder gateway so the full order flow
can be exercised end to end. Swapping in a real provider (Stripe, etc.) later
will not change this contract.

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/payments` | customer | Pay for own order in `pending`/`awaiting_payment`. |
| GET | `/payments/{payment_id}` | any user | Get one (customers: only for their own order). |
| GET | `/payments/order/{order_id}` | any user | List payments for an order. |

```json
// POST request
{ "order_id": "...", "method": "card", "provider": null }
```
```json
// response (201) -- status is "completed" immediately (manual gateway)
{
  "id": "...", "order_id": "...", "amount": "39.98", "currency": "USD",
  "status": "completed", "provider": "manual", "provider_reference": "manual-...",
  "method": "card", "paid_at": "2026-09-08T10:01:00Z", "created_at": "2026-09-08T10:01:00Z"
}
```
On success, the order moves to `paid` and a `Sale` record is created (see
backend architecture notes — sales are the immutable financial ledger,
separate from the mutable order).

## `/api/v1/shipments`

No real carrier is integrated yet — tracking numbers are placeholders
(`MANUAL-xxxxxxxxxx`). Swapping in a real carrier later will not change this
contract.

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/shipments/order/{order_id}` | staff | Start preparing a shipment (order must be `paid`). |
| POST | `/shipments/{shipment_id}/ship` | staff | Mark dispatched; decrements real stock, order → `shipped`. |
| POST | `/shipments/{shipment_id}/deliver` | staff | Mark delivered; order → `delivered`. |
| GET | `/shipments/order/{order_id}` | any user | Get the shipment for an order. |

```json
// POST /shipments/order/{order_id} request
{ "address_id": "...", "carrier": null }
```

**Confirmed response shape** for `GET /shipments/order/{order_id}` (and the
`POST` create/ship/deliver responses — same schema throughout the lifecycle):
```json
{
  "id": "e6996580-941b-4129-87ca-592150a50527",
  "order_id": "680f68f6-4288-4410-a792-ba3420eaf49f",
  "address_id": "24e39aa2-33fe-4ec9-ba4d-39f32d4ac8d8",
  "status": "in_transit",
  "carrier": "DHL",
  "tracking_number": "MANUAL-E699658094",
  "shipped_at": "2026-09-08T11:06:19.263086Z",
  "delivered_at": null,
  "created_at": "2026-09-08T11:06:19.038605Z",
  "updated_at": "2026-09-08T11:06:19.253758Z"
}
```
`status` progresses `pending → preparing → in_transit → delivered` (or
`failed`/`returned`). `address_id` and `updated_at` are real fields —
include them even though earlier notes didn't have them confirmed.

---

## What Django needs to configure

- `MERCADOEXPRESS_API_BASE_URL` — see Base URL table above.
- Store the JWT access/refresh token pair per Django session (or proxy login
  through a Django view that forwards to `/auth/login` and stores tokens
  server-side) — this API does not manage Django sessions itself.
- All money fields are strings with 2 decimal places (JSON has no reliable
  decimal type) — parse as `Decimal`, never `float`, on the Django side.
- All IDs are UUIDv4 strings.
- Timestamps are ISO 8601 UTC (`...Z` / `+00:00`).

## Test data now available (Fase 7)

An admin account and a demo catalog now exist on the shared dev database
(the one behind `backend-api`'s `docker compose up` / `POSTGRES_PORT` in
`.env`) so the full order → payment → shipment → delivery flow can be
exercised without any manual setup:

- 3 categories (Electronics, Home & Kitchen, Books), 7 products, each with
  real stock — see `backend-api/app/scripts/seed_demo_data.py` for the
  exact list (SKUs `ELEC-001`..`ELEC-003`, `HOME-001`..`HOME-002`,
  `BOOK-001`..`BOOK-002`). Re-run it any time to reset/top up (idempotent,
  never overwrites existing rows).
- An admin account for testing staff-only endpoints (create/edit
  products & categories, adjust inventory, manage shipments) — ask
  backend-api for the current dev credentials (not written here; seeded via
  `app/scripts/seed_admin.py` from `.env`, not committed anywhere).
- Confirmed end-to-end against the real containerized backend
  (2026-09-08): register → create address → create order → pay → admin
  creates shipment → ship → deliver. Order status walked
  `pending → paid → preparing → shipped(in_transit) → delivered` exactly as
  documented above.

## Open items / not yet implemented

- Real payment gateway integration (currently a manual/no-op gateway).
- Real shipping carrier integration (currently placeholder tracking numbers).
- Self-service admin/employee account provisioning endpoint — currently
  seed-script only (`app/scripts/seed_admin.py`), no way to promote a user
  to `employee` through the API yet (direct DB update or a future
  admin-only endpoint).
- Multi-warehouse inventory (currently single stock pool per product).

---
_Maintained by the backend-api service. Last updated: 2026-09-08 (Phase 1-6 + 7: auth, catalog, inventory, orders, payments, shipments, tests, Docker, admin/demo-data seeding, product search, confirmed shipment response shape, full E2E order flow verified)._
