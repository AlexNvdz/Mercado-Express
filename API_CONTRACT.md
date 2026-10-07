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
| DELETE | `/categories/{category_id}` | staff | Delete. `409` if any product still belongs to it; subcategories are kept with `parent_id` set to `null`. |

```json
{ "name": "Electronics", "description": "Gadgets and devices", "parent_id": null, "is_active": true }
```

## `/api/v1/products`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/products` | staff | Create product (also creates its zero-stock inventory row). |
| GET | `/products?category_id=&search=&include_inactive=&page=&page_size=` | none | Paginated list, optionally filtered by category and/or full-text-ish search. Only active products, unless `include_inactive=true`, which is staff-only: `401` without a token, `403` for customers. |
| GET | `/products/{product_id}` | none | Get one. Inactive products are still returned (check `is_active`); `POST /orders` rejects them with `404`, so the storefront must not offer them for purchase. |
| PATCH | `/products/{product_id}` | staff | Partial update. |
| DELETE | `/products/{product_id}` | staff | Delete. Also purges its stored image files (see below). |
| POST | `/products/{product_id}/images` | staff | Upload one image (`multipart/form-data`, field `file`). jpeg/png/webp only, max 5MB. |
| DELETE | `/products/{product_id}/images/{image_id}` | staff | Remove one image. Only detaches the DB row -- the file itself is only removed from storage when the whole product is deleted. |

```json
{
  "sku": "SKU-001",
  "name": "Wireless Mouse",
  "description": "2.4GHz wireless mouse",
  "category_id": "b3f2b6f0-1234-4a5b-9c1d-abcdef123456",
  "price": "19.99",
  "is_active": true,
  "images": [
    { "id": "...", "url": "http://127.0.0.1:8000/media/products/{product_id}/{uuid}.jpg", "position": 0, "created_at": "..." }
  ]
}
```
`price` is a decimal-as-string in responses (2 decimal places). `images` is returned on `GET`/list responses (empty array if none); it is not accepted on `POST`/`PATCH /products` -- images are managed only via the endpoints above. Image files are stored locally by backend-api under `MEDIA_ROOT` and served back out at `MEDIA_URL` (`/media` by default) -- `url` is an absolute link built from the request host, safe to use as-is in an `<img src>`.

## `/api/v1/inventory`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/inventory?low_stock=&include_inactive=&page=&page_size=` | staff | Paginated list of inventory rows of active products (`include_inactive=true` adds inactive products' rows). `low_stock=true` filters to rows where `quantity_available <= reorder_level` (for a dashboard alert -- replaces paging `GET /inventory/{id}` once per product). |
| GET | `/inventory/{product_id}` | none | Check availability for one product. |
| GET | `/inventory/{product_id}/history?page=&page_size=` | staff | Paginated history of manual stock changes (adjust / set levels), newest first. |
| POST | `/inventory/{product_id}/adjust` | staff | Add/remove stock by a signed delta. Recorded in the history. |
| PUT | `/inventory/{product_id}` | staff | Set absolute `quantity_on_hand` / `reorder_level`. Recorded in the history. |

```json
// GET /inventory/{product_id} response, and each item of GET /inventory
{
  "id": "...", "product_id": "...",
  "quantity_on_hand": 50, "quantity_reserved": 3, "quantity_available": 47,
  "reorder_level": 10, "updated_at": "2026-09-08T10:00:00Z"
}
```
`quantity_available = quantity_on_hand - quantity_reserved`. Reservations are
made automatically when an order is created, released when it is cancelled
or refunded, and turned into a real `quantity_on_hand` decrement when its
shipment is dispatched.

`GET /inventory` returns the standard `{items, total, page, page_size, pages}`
envelope (see Pagination), `items` shaped as above.

```json
// POST /inventory/{product_id}/adjust request
{ "delta": 50, "reason": "restock" }   // reason is optional, max 255 chars
```
`delta` is signed: positive adds stock, negative removes it. Rejected with
`409` if it would take `quantity_on_hand` below `quantity_reserved`.

```json
// PUT /inventory/{product_id} request
{ "quantity_on_hand": 100, "reorder_level": 10, "reason": "conteo físico" }   // reorder_level and reason are optional
```
Both numbers (when present) must be `>= 0`. Sets absolute levels rather than
adjusting by a delta. `409` if `quantity_on_hand` would go below
`quantity_reserved`.

```json
// each item of GET /inventory/{product_id}/history (standard page envelope)
{
  "id": "...", "product_id": "...", "kind": "adjust",          // adjust | set_levels
  "quantity_on_hand_before": 10, "quantity_on_hand_after": 7, "quantity_delta": -3,
  "reorder_level_before": 0, "reorder_level_after": 0,
  "reason": "Producto dañado",                                  // null if none was sent
  "actor": { "id": "...", "email": "admin@...", "full_name": "...", "role": "admin" },  // null if the user no longer exists
  "created_at": "2026-10-07T10:00:00Z"
}
```
The history is append-only. Stock movements caused by orders (reserve,
release, dispatch) are not recorded here, only manual staff changes.

## `/api/v1/orders`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/orders` | customer | Create an order: validates products, reserves stock, computes totals. |
| GET | `/orders?status=&page=&page_size=` | any user | Customers see only their own orders; staff see all. Optional `status`, repeatable (`?status=paid&status=preparing`); `total`/`pages` count the filter. Unknown status = `422`. |
| GET | `/orders/{order_id}` | any user | Get one (customers: only their own, else `404`). |
| GET | `/orders/{order_id}/history` | staff | Every status change of the order, oldest first (flat list, not paginated). |
| POST | `/orders/{order_id}/cancel` | any user | Cancel (only while `pending`); releases reserved stock. |
| PATCH | `/orders/{order_id}/status` | staff | Manual correction; only the targets in the table below. |

7 statuses total: `pending`, `paid`, `preparing`, `shipped`, `delivered`,
`cancelled`, `refunded` (no `awaiting_payment` -- removed 2026-09-12, see
`alembic/versions/6bf0432e1cd9_*`; a failed payment now leaves the order
`pending`, which was already retryable). Lifecycle: `pending → paid →
preparing → shipped → delivered`, with `cancelled` reachable from
`pending`/`paid`/`preparing`, and `refunded` reachable from `paid`.

Who moves the order through the normal flow:
- `pending → paid`: a completed `POST /payments`.
- `paid → preparing`: `POST /shipments/order/{order_id}` (or the manual
  `PATCH` below).
- `preparing → shipped`: `POST /shipments/{shipment_id}/ship`.
- `shipped → delivered`: `POST /shipments/{shipment_id}/deliver`.

Allowed targets for `PATCH /orders/{order_id}/status` (anything else is
`409`). Since 2026-10-06, `shipped` and `delivered` are no longer manual
targets: an order only gets there through its shipment, so it is never
shipped without a shipment and tracking number, and its stock is
fulfilled exactly once.

| Current | Allowed manual targets |
|---|---|
| `pending` | `cancelled` |
| `paid` | `preparing`, `cancelled`, `refunded` |
| `preparing` | `cancelled` |
| `shipped`, `delivered`, `cancelled`, `refunded` | none |

Moving to `cancelled` or `refunded`, whether through `PATCH` or
`POST /orders/{id}/cancel`, does three things. Both statuses are only
reachable before dispatch, so the goods never left:
- Releases the reserved stock. Since 2026-10-06 `refunded` does this too;
  before, the reservation leaked.
- If the order had been paid, appends a negative `reversal` entry to the
  sales ledger (see `/api/v1/reports`). The original sale entry is never
  edited or deleted, and an order is reversed at most once.
- Moves an undispatched shipment (`pending`/`preparing`) to `cancelled`.

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
  "shipping_address": {
    "id": "c4a1...", "user_id": "...", "line1": "Calle 10 # 20-30", "line2": null,
    "city": "Bogotá", "state": "Bogotá D.C.", "postal_code": "110111", "country": "CO",
    "is_default": true, "created_at": "...", "updated_at": "..."
  },
  "items": [
    { "id": "...", "product_id": "b3f2b6f0-...", "quantity": 2, "unit_price": "19.99", "line_total": "39.98" }
  ],
  "created_at": "2026-09-08T10:00:00Z", "updated_at": "2026-09-08T10:00:00Z"
}
```
`409` if any item is out of stock — no partial reservation is made (all-or-nothing).

`shipping_address` is the resolved address object (`null` if the order has no
`shipping_address_id`) — added so staff can see where to ship without a
separate address-lookup call; every `OrderOut` response (create, get, list,
status update) includes it.

```json
// each item of GET /orders/{order_id}/history
{
  "id": "...", "order_id": "...",
  "from_status": "paid", "to_status": "preparing",   // from_status is null only for the first entry
  "source": "shipment_created",
  "actor": { "id": "...", "email": "admin@...", "full_name": "...", "role": "admin" },  // null if the user no longer exists
  "created_at": "2026-10-07T10:00:00Z"
}
```
`source` is one of `order_created` (POST /orders), `payment` (completed
POST /payments), `manual` (PATCH /orders/{id}/status), `customer_cancel`
(POST /orders/{id}/cancel), `shipment_created`, `shipment_dispatched`,
`shipment_delivered`. The history is append-only.
- A rejected transition (`409`) leaves no entry.
- Creating a shipment for an order that staff already moved to
  `preparing` changes no status, so it leaves no entry either.
- The history starts when migration `377398800f5e` is applied: older
  orders have no entries, or only the ones made after it.

## `/api/v1/payments`

No real payment gateway is integrated yet — `POST /payments` completes the
payment immediately via a manual/placeholder gateway so the full order flow
can be exercised end to end. Swapping in a real provider (Stripe, etc.) later
will not change this contract.

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/payments` | customer | Pay for own order in `pending`. |
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
On success, the order moves to `paid` and a `sale` entry is appended to the
sales ledger (the append-only financial record, separate from the mutable
order; see `/api/v1/reports`).

## `/api/v1/shipments`

No real carrier is integrated yet. Staff can enter the carrier and tracking
number; if no tracking number was entered by dispatch time, a placeholder
(`MANUAL-xxxxxxxxxx`) is generated. Swapping in a real carrier later will
not change this contract.

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/shipments/order/{order_id}` | staff | Create the shipment (order must be `paid` or `preparing`); order → `preparing`. |
| PATCH | `/shipments/{shipment_id}` | staff | Edit `carrier` / `tracking_number`; only before dispatch. |
| POST | `/shipments/{shipment_id}/ship` | staff | Mark dispatched; decrements real stock, order → `shipped`. |
| POST | `/shipments/{shipment_id}/deliver` | staff | Mark delivered; order → `delivered`. |
| GET | `/shipments/order/{order_id}` | any user | Get the shipment for an order. |

```json
// POST /shipments/order/{order_id} request
{ "address_id": "...", "carrier": "DHL", "tracking_number": "1Z999AA10123456784" }
```
- `address_id` is required. `carrier` and `tracking_number` are optional
  (max 100 chars each); a blank or whitespace-only value is stored as `null`.
- The order must be `paid` (it moves to `preparing`) or already `preparing`
  (staff moved it there by hand; it stays `preparing`). Otherwise `409`.
- One shipment per order: `409` if the order already has one.
- The shipment is created with status `preparing`.

```json
// PATCH /shipments/{shipment_id} request -- every key optional
{ "carrier": "Servientrega", "tracking_number": "SV-123456" }
```
Only the keys sent are changed; `null` (or blank) clears a field. Allowed
while the shipment is `pending` or `preparing`, else `409`. Returns the
shipment.

`POST /shipments/{shipment_id}/ship` requires the shipment to be
`preparing` and its order `preparing` (else `409`). It keeps the tracking
number staff entered, or generates `MANUAL-...` if there is none. It turns
the order's stock reservation into a real decrement, exactly once: a
second call is a `409` and touches no stock. `deliver` requires the
shipment to be `in_transit`.

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
`failed`/`returned`). Since 2026-10-06 there is also `cancelled`: an
undispatched shipment whose order was cancelled or refunded. It can be
neither edited nor dispatched. `address_id` and `updated_at` are real
fields — include them even though earlier notes didn't have them confirmed.

## `/api/v1/reports`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/reports/summary?top_products_limit=` | staff | Aggregate dashboard numbers, computed server-side from the sales ledger (not `Order.total_amount`). |

The sales ledger is append-only. Each order has at most two entries, never
edited or deleted:
- a `sale` entry (positive), written when its payment completes;
- a `reversal` entry (the same amount, negated), written if that paid order
  is later cancelled or refunded.

Revenue is therefore net of returns. Paid orders that were cancelled or
refunded before 2026-10-06 got their reversal entries backfilled by the
migration (`bdd517b5e052`).

```json
{
  "net_revenue": "1049.98",
  "gross_revenue": "1249.98",
  "refunded_amount": "200.00",
  "sale_count": 12,
  "reversal_count": 2,
  "orders_by_status": [
    { "status": "pending", "count": 2 },
    { "status": "paid", "count": 3 },
    { "status": "preparing", "count": 1 },
    { "status": "shipped", "count": 2 },
    { "status": "delivered", "count": 4 },
    { "status": "cancelled", "count": 1 },
    { "status": "refunded", "count": 0 }
  ],
  "top_products": [
    { "product_id": "...", "name": "Wireless Mouse", "sku": "ELEC-001", "units_sold": 14, "revenue": "279.86" }
  ],
  "customer_count": 8,
  "product_count": 7,
  "generated_at": "2026-09-12T10:00:00Z"
}
```
- `gross_revenue`: sum of the `sale` entries, i.e. every order ever paid.
- `refunded_amount`: sum of the `reversal` entries, as a positive amount.
- `net_revenue`: `gross_revenue - refunded_amount`, i.e. the sum of the
  whole ledger.
- `sale_count`: number of `sale` entries. Reversals are not counted here.
- `reversal_count`: number of `reversal` entries.
- Changed 2026-10-06: `total_revenue` was removed. Use `net_revenue`.
- All money fields are 2dp strings, including `"0.00"` when the ledger is
  empty.

`orders_by_status` always lists every `OrderStatus` value, `count: 0` if none.
`top_products` is ordered by `units_sold` descending, capped at
`top_products_limit` (default 10, max 100). Each product's
`revenue`/`units_sold` is summed from `order_items` of orders that were paid
and not reversed. Orders that were never paid (still `pending`, cancelled
before payment, etc.) never contribute, and neither do paid orders that were
later cancelled or refunded.

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
_Maintained by the backend-api service. Last updated: 2026-10-07 (`GET /orders?status=` filter; staff-only `include_inactive` on `GET /products` and `GET /inventory`, which now hides inactive products' rows by default; append-only `GET /orders/{id}/history` and `GET /inventory/{id}/history`; `PUT /inventory` takes `reason` and returns `409` below reserved stock). Previous update 2026-10-06 (net revenue: sales ledger gets `reversal` entries, `GET /reports/summary` returns `net_revenue`/`gross_revenue`/`refunded_amount`/`reversal_count` instead of `total_revenue`; shipment flow: create from `paid` or `preparing` with `carrier`/`tracking_number`, new `PATCH /shipments/{id}`, new shipment status `cancelled`, `shipped`/`delivered` no longer manual order targets, refund releases reserved stock). Previous update 2026-09-12: added `GET /reports/summary` and `GET /inventory` batched/low-stock list; documented inventory adjust/set payload shapes._
