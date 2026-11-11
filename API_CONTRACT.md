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
`{"detail": [...]}` with field-level errors), `502` (since 2026-11-11: the
shipping provider Envia.com failed or refused the request; `detail` is a
string with its reason).

The services validate before writing, so the database rarely rejects a
change. When it does (since 2026-10-22, instead of a `500`), the response
names the constraint: a foreign key or unique violation is `409`, a CHECK
or NOT NULL violation is `422`, with `detail` as a string:
```json
// 409
{ "detail": "The database rejected the change: foreign key constraint 'order_items_product_id_fkey' on table 'order_items'." }
```

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
| GET | `/customers?search=&page=&page_size=` | staff | Paginated list of customers, newest first. Optional `search`: case-insensitive match on full name, email or phone (since 2026-10-22). |
| GET | `/customers/{customer_id}` | staff | Get one customer. |

Address body:
```json
{
  "line1": "Carrera 43A # 1-50",
  "line2": "Apto 301",
  "city": "Envigado",
  "state": "Antioquia",
  "country": "CO",
  "phone": "3007654321",
  "is_default": true
}
```
Since 2026-11-11 (Envia.com shipping):
- `phone` (optional, max 30) is who receives the package. Carriers require
  one; an address without it falls back to the customer's profile phone.
- A Colombian address (`country` `CO`) must name a city Envia knows in that
  department, else `422` with a Spanish `detail` string ("La ciudad 'X' no
  existe en el departamento 'Y'."). `state` is the department's name or its
  code from `GET /locations/co/states`. The backend sets `postal_code` from
  the city, so it is optional on create (sent or not, it's replaced). If
  Envia can't be reached, a sent `postal_code` is kept unchecked; without one
  it's a `502`. A `PATCH` that touches `city`/`state`/`country`/`postal_code`
  is checked the same way.
- Outside Colombia `postal_code` stays required (`422` without it).

## `/api/v1/locations`

Since 2026-11-11. Public. What the address form offers.

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/locations/co/states` | public | The 33 Colombian departments: `[{"code": "AN", "name": "Antioquia"}, ...]`. |
| GET | `/locations/co/states/{state}/cities` | public | `["Abejorral", ..., "Medellín", ...]`: every town and vereda Envia knows there, sorted. `state` is a code or a name. `404` unknown department. |

Departments are a fixed table in the backend. Cities come from Envia's
geocodes and are cached in the API's memory (first call per department
~1 s, a few hundred to ~1,900 names).

## `/api/v1/categories`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/categories` | staff | Create category (optionally `parent_id` for subcategories). |
| GET | `/categories?with_products=&sort=&page=&page_size=` | none | Paginated list, by name. `with_products=true`: only categories with at least one active product. `sort=products`: most active products first, then by name (any other `sort` than `name`/`products` = `422`). Both combine with pagination; `total` counts the filter. |
| GET | `/categories/{category_id}` | none | Get one. |
| PATCH | `/categories/{category_id}` | staff | Partial update. |
| DELETE | `/categories/{category_id}` | staff | Delete. `409` if any product still belongs to it; subcategories are kept with `parent_id` set to `null`. |

```json
// POST request
{ "name": "Electronics", "description": "Gadgets and devices", "parent_id": null, "is_active": true }
```
```json
// response of every endpoint above (create, list item, get, update)
{
  "id": "...", "name": "Electronics", "description": "Gadgets and devices", "parent_id": null,
  "is_active": true, "active_product_count": 3, "created_at": "...", "updated_at": "..."
}
```
`active_product_count` (since 2026-10-23) is the number of products in the
category with `is_active: true`, the ones the public catalog shows. Inactive
products (e.g. the imported Olist ones) are not counted.

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
  "price": "39900.00",
  "is_active": true,
  "images": [
    { "id": "...", "url": "http://127.0.0.1:8000/media/products/{product_id}/{uuid}.jpg", "position": 0, "created_at": "..." }
  ]
}
```
`price` is a decimal-as-string in responses (2 decimal places). Since 2026-11-10 `POST`/`PATCH /products` reject a `price` below `5900.00` (`MIN_PRODUCT_PRICE` in `app/schemas/product.py`) with `422`; `5900.00` itself is accepted. Rows priced lower before that date (Olist BRL prices, old demo data) are still returned as is by `GET`, but cannot be bought (see `POST /orders`). `images` is returned on `GET`/list responses (empty array if none); it is not accepted on `POST`/`PATCH /products` -- images are managed only via the endpoints above. Image files are stored locally by backend-api under `MEDIA_ROOT` and served back out at `MEDIA_URL` (`/media` by default) -- `url` is an absolute link built from the request host, safe to use as-is in an `<img src>`.

## `/api/v1/inventory`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/inventory?low_stock=&include_inactive=&product_id=&search=&page=&page_size=` | staff | Paginated list of inventory rows of active products (`include_inactive=true` adds inactive products' rows). `low_stock=true` filters to rows where `quantity_available <= reorder_level` (for a dashboard alert -- replaces paging `GET /inventory/{id}` once per product). `product_id` (repeatable, at most 100: `?product_id=a&product_id=b`) keeps only those products' rows, e.g. the products on one screen in a single request; more than 100 = `422`. `search`: case-insensitive match on product name or SKU. All filters combine (AND). |
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
envelope (see Pagination), `items` shaped as above plus, since 2026-10-22,
three fields of the row's product (only in this list, not in the single-row
responses):
```json
{ "...": "...", "product_name": "Wireless Mouse", "product_sku": "ELEC-001", "product_is_active": true }
```

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
| POST | `/orders/checkout` | customer | `POST /orders` + `POST /payments` in one transaction (see below). |
| GET | `/orders?status=&search=&created_from=&created_to=&page=&page_size=` | any user | Customers see only their own orders; staff see all. Newest first. Optional `status`, repeatable (`?status=paid&status=preparing`); unknown status = `422`. Since 2026-10-22: `search` (case-insensitive match on order number, customer email or customer full name) and `created_from` / `created_to` (`YYYY-MM-DD`, inclusive, UTC days: `created_to=2026-10-22` includes everything up to 23:59:59 UTC that day; another format = `422`). Since 2026-11-11: `country` (2-letter ISO code of the shipping address, case-insensitive, e.g. `CO`; `status=paid&country=CO` is the panel's "paid without a label" list). All filters combine (AND); `total`/`pages` count them. |
| GET | `/orders/{order_id}` | any user | Get one (customers: only their own, else `404`). |
| GET | `/orders/{order_id}/history` | staff | Every status change of the order, oldest first (flat list, not paginated). |
| POST | `/orders/{order_id}/cancel` | any user | Cancel (only while `pending`); releases reserved stock. |
| PATCH | `/orders/{order_id}/status` | staff | Manual correction; only the targets in the table below. |

7 statuses total: `pending`, `paid`, `preparing`, `shipped`, `delivered`,
`cancelled`, `refunded` (no `awaiting_payment` -- removed 2026-09-12, see
`alembic/versions/6bf0432e1cd9_*`; a failed payment now leaves the order
`pending`, which was already retryable). Lifecycle: `pending → paid →
preparing → shipped → delivered`, with `cancelled` reachable from
`pending`/`paid`/`preparing`, and `refunded` reachable from `paid` (and,
since 2026-11-10, from `delivered` only through an approved support claim,
see `/api/v1/soporte`).

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
  "subtotal": "79800.00", "tax_amount": "0.00", "shipping_amount": "20000.00", "total_amount": "99800.00",
  "shipping_address_id": "c4a1...", "notes": "Leave at front door",
  "shipping_address": {
    "id": "c4a1...", "user_id": "...", "line1": "Calle 10 # 20-30", "line2": null,
    "city": "Bogotá", "state": "Bogotá D.C.", "postal_code": "110111", "country": "CO",
    "phone": "3001234567", "is_default": true, "created_at": "...", "updated_at": "..."
  },
  "items": [
    { "id": "...", "product_id": "b3f2b6f0-...", "product_name": "Wireless Mouse", "product_sku": "ELEC-001",
      "quantity": 2, "unit_price": "39900.00", "line_total": "79800.00" }
  ],
  "created_at": "2026-09-08T10:00:00Z", "updated_at": "2026-09-08T10:00:00Z"
}
```
`shipping_amount` is the flat `FLAT_SHIPPING_FEE` per order (since
2026-11-11 set to `20000.00` COP in `.env`, whatever the items or the city;
the store pays the real Envia cost, see `shipping_cost` on the shipment).
`409` if any item is out of stock — no partial reservation is made (all-or-nothing).
`422` if any product is priced below `5900.00` (a row that predates the
minimum, e.g. `0.00`): nothing is reserved or saved.

`shipping_address` is the resolved address object (`null` if the order has no
`shipping_address_id`) — added so staff can see where to ship without a
separate address-lookup call; every `OrderOut` response (create, get, list,
status update) includes it.

Since 2026-10-22 each item also carries `product_name` and `product_sku`
(the product's current name and SKU, so order screens don't need a
`GET /products/{id}` per line; the price stays the `unit_price` snapshot).

Since 2026-10-22 every `OrderOut` response also includes `payments`: the
order's payments, same shape as the `/api/v1/payments` responses (`[]` while
unpaid). Additive; no other field changed.

`POST /orders/checkout` takes the `POST /orders` body plus an optional
`method` (same as `POST /payments`):
```json
{ "items": [{ "product_id": "b3f2b6f0-...", "quantity": 2 }], "shipping_address_id": null, "notes": null, "method": "card" }
```
It creates the order, its items, the stock reservation, the payment and the
sales-ledger `sale` entry in a single transaction, and answers `201` with the
`OrderOut` (`status: "paid"`, one `completed` payment in `payments`). If any
step raises an error, nothing is saved: no order, no reservation, no payment.
(A payment a future real gateway declines would not raise: as with
`POST /payments`, the order stays `pending` with a `failed` payment.) Same
errors as `POST /orders` (`404` unknown/inactive product or address, `409`
insufficient stock, `422` product priced below the minimum). `POST /orders` and `POST /payments` are unchanged.

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
`shipment_delivered`, `support_claim` (refund approved by POST
/soporte/procesar-reclamo, actor = the customer). The history is append-only.
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
| POST | `/payments` | customer | Pay for own order in `pending`. `422` if the order total is `0.00`. |
| GET | `/payments/{payment_id}` | any user | Get one (customers: only for their own order). |
| GET | `/payments/order/{order_id}` | any user | List payments for an order. |

```json
// POST request
{ "order_id": "...", "method": "card", "provider": null }
```
```json
// response (201) -- status is "completed" immediately (manual gateway)
{
  "id": "...", "order_id": "...", "amount": "79800.00", "currency": "USD",
  "status": "completed", "provider": "manual", "provider_reference": "manual-...",
  "method": "card", "paid_at": "2026-09-08T10:01:00Z", "created_at": "2026-09-08T10:01:00Z"
}
```
On success, the order moves to `paid` and a `sale` entry is appended to the
sales ledger (the append-only financial record, separate from the mutable
order; see `/api/v1/reports`).

## `/api/v1/shipments`

Two ways to get a shipment:
- **Envia.com** (since 2026-11-11, only with `ENVIA_API_KEY` set and a
  Colombian shipping address): once a payment completes (`POST
  /orders/checkout` or `POST /payments`), the backend buys the cheapest
  label among `ENVIA_CARRIERS` in the background, right after the response,
  and creates the shipment with it. The order moves to `preparing`, with an
  `order_status_history` row `source=shipment_created` and no actor. If that
  fails (no phone, no coverage, Envia down), the order stays `paid` and
  staff retry with `POST /shipments/order/{order_id}/envia`, or all of
  them at once with `POST /shipments/envia/retry`. Once the label exists,
  Envia's tracking webhook (`POST /webhooks/envia`, below) dispatches and
  delivers the shipment on its own.
  Cash-on-delivery services (`*_cod`) and the to-office ones in
  `ENVIA_EXCLUDED_SERVICES` are never picked.
- **Manual**: staff enter the carrier and tracking number; if no tracking
  number was entered by dispatch time, a placeholder (`MANUAL-xxxxxxxxxx`)
  is generated.

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/shipments/order/{order_id}` | staff | Create the shipment (order must be `paid` or `preparing`); order → `preparing`. |
| POST | `/shipments/order/{order_id}/envia` | staff | Buy the cheapest Envia label for the order's shipping address and create the shipment with it (same rules as above). No body. `201` shipment; `409` not `paid`/`preparing` or already has a shipment; `422` no address, not in Colombia, unknown city, no phone or Envia not configured; `502` Envia failed (`detail` says why). |
| POST | `/shipments/envia/retry` | staff | Buy the Envia label of up to 10 `paid` orders with a Colombian address (a paid order never has a shipment), newest first, each on its own: one failing doesn't undo the others. No body. `200` `{"created": 1, "failed": [{"order_id", "order_number", "detail"}], "remaining": 1}`; `remaining` counts the paid CO orders still without a label (failures included). `422` if Envia is not configured. |
| POST | `/shipments/{shipment_id}/sync` | staff | Read the Envia label's tracking: `Picked Up`/`Shipped`/`In Transit`/`Out for Delivery` dispatch it (same as `/ship`), `Delivered` delivers it (dispatching first if needed); any other status changes nothing. Returns the shipment plus `carrier_status` (Envia's status name, e.g. `"Created"`). `422` if the shipment has no Envia label. |
| PATCH | `/shipments/{shipment_id}` | staff | Edit `carrier` / `tracking_number`; only before dispatch, and never on an Envia label (`409`). |
| POST | `/shipments/{shipment_id}/ship` | staff | Mark dispatched; decrements real stock, order → `shipped`. |
| POST | `/shipments/{shipment_id}/deliver` | staff | Mark delivered; order → `delivered`. |
| GET | `/shipments/order/{order_id}` | any user | Get the shipment for an order. |

Since migration `9c4e2a7b1d35` the database enforces two dates: an
`in_transit` shipment has `shipped_at` (`ck_shipments_in_transit_has_shipped_at`)
and a `delivered` one has `delivered_at` (`ck_shipments_delivered_has_delivered_at`).
The endpoints above always set them, so their behavior does not change.

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
  "service": null,
  "label_url": null,
  "tracking_url": null,
  "shipping_cost": null,
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

Since 2026-11-11 an Envia shipment also fills `service` (e.g.
`"mensajeria_od"`), `label_url` (printable PDF hosted by Envia),
`tracking_url` (Envia's public tracking page) and `shipping_cost` (decimal
string, what Envia charged the store). The customer's
`GET /shipments/order/{order_id}` returns `label_url` and `shipping_cost` as
`null`; staff see them. All four are `null` on manual shipments.
Cancelling or refunding an order whose undispatched shipment has an Envia
label also voids the label at Envia (in the background, after the change
commits; a failure there only logs, the order stays cancelled).

## `/api/v1/webhooks`

Inbound calls from third parties: no JWT, each guarded by its own secret.

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/webhooks/envia?token=` | `token` = `ENVIA_WEBHOOK_TOKEN`, plus the signature when sent | Envia's tracking webhook (type 3 `simpleTracking`). Two bodies, both seen from the sandbox on 2026-11-11: real deliveries `{"type": "tracking.simple", "created_at": "...", "data": {"shipment_id": 187528, "tracking_number": "INTESBX893874", "status": "Created", "carrier_name": "interRapidisimo"}}` (one arrives when the label is bought), and Envia's test call (`POST /ship/webhooktest/`) a flat `{"carrier", "tracking_number", "shipment_status": "Picked Up"}`. The status moves the shipment exactly like `/sync` (case, spaces and `_` ignored), with no actor in the history; repeats and statuses already passed change nothing. Always `200` `{"applied": true|false}` once authenticated: `true` when it's one of our Envia labels (even if nothing moved), `false` for an unknown tracking number, a non-tracking event or a transition that can't apply, so Envia doesn't retry. `401` wrong token, or (with `ENVIA_WEBHOOK_SECRET` set) a wrong `X-Webhook-Signature`: real deliveries carry `X-Webhook-Signature: v1=<hex HMAC-SHA256(auth_token, "<X-Webhook-Timestamp>.<X-Webhook-Event>.<raw body>")>`, `auth_token` being the webhook's own field in `GET queries.../webhooks`; the test call is unsigned and passes on the token alone. `404` while `ENVIA_WEBHOOK_TOKEN` is unset. Register/repoint the URL with `uv run python -m app.scripts.envia_webhook https://<public-host>` (prints the `auth_token`). |

## `/api/v1/reports`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/reports/summary?top_products_limit=` | staff | Aggregate dashboard numbers, computed server-side from the sales ledger (not `Order.total_amount`). Cached for up to 10 s (`REPORT_CACHE_SECONDS`): a new sale can take that long to show; `generated_at` says when the numbers were computed. |

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
  "sales_by_region": [
    { "region": "SP", "net_revenue": "799.98", "order_count": 8 },
    { "region": "Sin dirección", "net_revenue": "250.00", "order_count": 4 }
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

`sales_by_region` lists every region, ordered by `net_revenue` descending
(no limit: the Olist data has 27 states plus a few demo ones):
- `region`: the `state` of the order's shipping address, or
  `"Sin dirección"` for orders without one.
- `net_revenue`: sum of the ledger (`sale` and `reversal` entries) for the
  region's orders, the same basis as `net_revenue`, so the regions add up to
  the headline figure.
- `order_count`: orders with a `sale` entry (ever paid), including ones later
  cancelled or refunded; the regions add up to `sale_count`.
- Known caveat: BRL and USD amounts are summed as is, with no currency
  conversion. The same is true of `net_revenue`.
- Added 2026-10-23.

---

## `/api/v1/soporte`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/soporte/procesar-reclamo` | any user | Free-text claim. A local LLM (Ollama, `OLLAMA_MODEL`, default `qwen2.5:7b`) extracts the intent; fixed rules then decide. |

```jsonc
// request
{ "mensaje": "el pedido 3F2B8C1E-9D4A-4E7B-A6C2-1F0E9D8C7B6A llegó roto, devuélvanme la plata" }  // 10..2000 chars
// response, always 200 (401 without login, 422 for a bad body)
{
  "decision": "aprobado",          // aprobado | rechazado | revision_manual
  "motivo": "Reembolso aprobado.", // Spanish, shown to the customer
  "order_id": "3f2b8c1e-...",      // null when no order was looked at
  "order_status": "refunded"       // the order's status after the decision, or null
}
```
Rules, in order (the first that applies wins):
1. LLM down, timed out or invalid answer: `revision_manual`.
2. Extracted UUID not literally in `mensaje` (case-insensitive): `revision_manual`.
3. Action is not `reembolso` (`cancelacion`, `estado_pedido`, `otro`): `revision_manual`.
4. LLM confidence `<= 0.85`: `revision_manual`.
5. No UUID in the message: `revision_manual`.
6. Order missing or not the caller's: `rechazado` ("Pedido no encontrado.", same answer for both).
7. Order not `delivered`: `rechazado`.
8. Shipment has no `delivered_at`: `revision_manual`.
9. More than 30 days since `delivered_at`: `rechazado`.
10. Otherwise `aprobado`: the order goes `delivered -> refunded`, a `reversal` is
    appended to the ledger and the history gets a `support_claim` entry. Stock,
    payment (`completed`) and shipment (`delivered`) are not changed.

`delivered -> refunded` is not a `PATCH /orders/{id}/status` target: only this
endpoint can do it. Added 2026-11-10.

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
_Maintained by the backend-api service. Last updated: 2026-11-10 (`POST /soporte/procesar-reclamo`, `support_claim` history source, `delivered -> refunded` through a support claim). Previous update 2026-10-23 (`sales_by_region` on `GET /reports/summary`). Previous update 2026-10-07 (`GET /orders?status=` filter; staff-only `include_inactive` on `GET /products` and `GET /inventory`, which now hides inactive products' rows by default; append-only `GET /orders/{id}/history` and `GET /inventory/{id}/history`; `PUT /inventory` takes `reason` and returns `409` below reserved stock). Previous update 2026-10-06 (net revenue: sales ledger gets `reversal` entries, `GET /reports/summary` returns `net_revenue`/`gross_revenue`/`refunded_amount`/`reversal_count` instead of `total_revenue`; shipment flow: create from `paid` or `preparing` with `carrier`/`tracking_number`, new `PATCH /shipments/{id}`, new shipment status `cancelled`, `shipped`/`delivered` no longer manual order targets, refund releases reserved stock). Previous update 2026-09-12: added `GET /reports/summary` and `GET /inventory` batched/low-stock list; documented inventory adjust/set payload shapes._
