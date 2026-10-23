# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repo shape

One git repo (root, GitHub: `AlexNvdz/Mercado-Express`) holding two independent projects, each with its own `uv`-managed venv and test suite. Not a monorepo build — no root package manifest, no shared dependency graph.

- `backend-api/` — FastAPI + PostgreSQL. Owns all business data (customers, products, inventory, orders, payments, shipments, sales).
- `front-end/` — Django. No business logic, no direct DB access to business data. Talks to `backend-api` only over HTTP through `services/`.
- `API_CONTRACT.md` (root) — source of truth for the HTTP contract between them. Maintained by backend-api, read by front-end. Update it whenever an endpoint changes; the frontend should not need backend source to integrate.
- `front-end/API_INTEGRATION_NOTES.md` — frontend-side log of what's been verified against the real backend, open questions for backend-api, and frontend-only decisions. Check it before assuming an endpoint shape.

Django must never connect directly to PostgreSQL for business data — all reads/writes of Customers, Products, Inventory, Orders, Payments, Shipments, Sales go through the API.

## backend-api (FastAPI)

Stack: Python 3.12, FastAPI, SQLAlchemy 2.x async (`psycopg[binary]` v3), Alembic, Pydantic v2, PyJWT, pytest, Ruff, mypy. Dependency management via `uv`.

```bash
cd backend-api
uv sync
docker compose up -d db              # Postgres only; api service in compose runs full build
uv run alembic upgrade head
uv run uvicorn app.main:app --reload

uv run pytest                        # full suite
uv run pytest tests/test_orders.py   # single file
uv run pytest tests/test_orders.py::test_name  # single test
uv run pytest --cov=app

uv run ruff check .
uv run ruff format .
uv run mypy app

uv run alembic revision --autogenerate -m "message"  # needs a running DB
```

Windows-only gotcha: always run uvicorn with `--reload` outside Docker — psycopg3 async can't use the default `ProactorEventLoop`, and `--reload` is what makes uvicorn spawn a compatible loop. Without it: `psycopg.InterfaceError: Psycopg cannot use the 'ProactorEventLoop'...`.

Tests run against a real PostgreSQL `mercadoexpress_test` database (native UUID/ENUM/CHECK constraints matter), each test wrapped in a rolled-back transaction. Create the test DB once with `createdb` before first run (see `backend-api/README.md`).

### Architecture (layered, one direction of dependency)

```
routers/v1/*  ->  services/*  ->  repositories/*  ->  models/* (SQLAlchemy ORM)
                       |
                  schemas/* (Pydantic, request/response shape)
```

- `models/` — one ORM file per entity, plus shared `enums.py`.
- `repositories/` — data access only (generic `base.py` + per-entity query methods). No business rules here.
- `services/` — business logic and orchestration (order flow, auth, stock reservation). This is where invariants live.
- `schemas/` — Pydantic request/response models, decoupled from ORM models.
- `routers/v1/` — one router per resource, aggregated into `routers/v1/api.py`.
- `dependencies.py` — `get_current_user`, `require_roles`/`require_staff`/`require_admin`, pagination params.
- `exceptions.py` — domain exceptions mapped to HTTP status codes in `main.py`.
- Async ORM gotcha: every relationship a response schema serializes (e.g. `OrderOut.items`, `OrderOut.shipping_address`) must be eager-loaded with `selectinload` in the repository query, and an object changed after a `flush` needs `await db.refresh(obj, ["updated_at", ...])` before it is returned (see `OrderService.transition_status`). Name the attributes: a bare `refresh(order)` cascades to `order.items` (`cascade="all"` includes refresh-expire) and expires their eager-loaded `product`, which `OrderItemOut.product_name` then lazy-loads. Otherwise Pydantic triggers an async lazy-load and the request fails with `MissingGreenlet` instead of a clear error.

Key domain rules to know before touching orders/inventory/payments:

- **Auth**: single `users` table, `role` enum (`customer`/`employee`/`admin`) rather than per-role tables. No self-service staff/admin provisioning — those accounts are created directly in the DB.
- **Orders vs Sales**: `Order` is mutable lifecycle state (`pending -> paid -> preparing -> shipped -> delivered`, with `cancelled`/`refunded` branches — see `API_CONTRACT.md` for the full transition table). 7 statuses total, no separate `awaiting_payment` (removed 2026-09-12: a failed payment leaves the order `pending`, already retryable from there). `Sale` is the append-only financial ledger, never edit or delete a row to fix an order. Each row has a `kind` (`SaleKind`): a `sale` entry (positive) is written when a payment completes, and a `reversal` entry (negative, same amount) is appended when that paid order is later cancelled or refunded (`OrderService.record_reversal`, idempotent; unique on `(order_id, kind)`, sign enforced by a CHECK). Net revenue is the sum of the whole ledger.
- **Who changes an order's status**: other resources drive the normal flow. A completed `POST /payments` (`PaymentService`) moves `pending -> paid` and writes the `Sale`; `POST /orders/checkout` (`OrderService.checkout`) runs `create_order` + `create_payment` in the request's one transaction, so the order, items, reservation, payment and `Sale` are saved together or not at all (`POST /orders`/`POST /payments` unchanged); `ShipmentService` creates the shipment (carrier + tracking number, editable via `PATCH /shipments/{id}` until dispatch) from a `paid` or `preparing` order and leaves it `preparing`, then moves it `-> shipped` (dispatch, fulfills stock once) and `-> delivered`. `PATCH /orders/{id}/status` (staff) is for manual corrections only, checked against `_ALLOWED_TRANSITIONS` in `app/services/order_service.py` (invalid jump = `409`): only `pending -> cancelled`, `paid -> preparing/cancelled/refunded` and `preparing -> cancelled`. `pending -> paid` is absent (only a real payment writes the `Sale`), and `shipped`/`delivered` are reachable only through the shipment, so an order can't ship without one. Cancelling/refunding releases reserved stock, appends the ledger reversal if the order was paid, and marks an undispatched shipment `cancelled`. Every status change locks the order row (`SELECT ... FOR UPDATE`) so a double-submitted dispatch can't fulfill stock twice, and appends a row to the append-only `order_status_history` (actor, from/to, `source`: order_created / payment / manual / customer_cancel / shipment_*), read by staff via `GET /orders/{id}/history`. Manual stock changes (adjust, set levels) likewise go to `inventory_history` with before/after values and the `reason` (`GET /inventory/{id}/history`); stock moves caused by orders are not recorded there. The frontend mirrors the table in `services/orders.py::ORDER_TRANSITIONS` — change both together.
- **Inventory**: single stock pool per product (`quantity_on_hand` / `quantity_reserved`; `quantity_available` is derived). Reserve/release/fulfill use `SELECT ... FOR UPDATE` row locks to prevent overselling under concurrent orders. Order creation is all-or-nothing — no partial stock reservation across items.
- **Payments/Shipments**: sit behind `PaymentGateway` / `ShipmentCarrier` provider abstractions with only a manual/placeholder implementation wired up (no real gateway or carrier yet, by design). `POST /payments` completes payment immediately via the manual gateway.
- **Product images** (`app/models/product_image.py`): a product has many `ProductImage` rows (`product_id`, `file_path`, `position`). Storage sits behind an `ImageStorage` port (`app/services/storage_service.py`), same pattern as `PaymentGateway`/`ShipmentCarrier` -- only `LocalDiskImageStorage` is wired up (no S3/cloud storage; writes under `MEDIA_ROOT`, served at `MEDIA_URL`, absolute URL built with `PUBLIC_BASE_URL` since the frontend is a different origin/port). `POST`/`DELETE /products/{id}/images` manage rows one at a time; deleting a single row never touches disk -- files are only purged in bulk when the whole product is deleted (`ProductService.delete`).
- **Reports**: `GET /reports/summary` (staff) returns `net_revenue`, `gross_revenue`, `refunded_amount`, `sale_count` and `reversal_count` from the `Sale` ledger (not `Order.total_amount`), order counts by status, top products by units sold, `sales_by_region` (net ledger total and paid-order count per shipping-address `state`, `"Sin dirección"` when the order has none; every region, net desc, adding up to `net_revenue`; BRL and USD summed as is, no conversion) and customer/product counts (`report_service.py` / `report_repository.py`). It is cached in process memory for `REPORT_CACHE_SECONDS` (default 10; the uncached aggregate takes ~200 ms on the Olist data, ~45 ms of it the region query), expiry only, no invalidation on writes; `tests/conftest.py` sets it to 0. `GET /inventory?low_stock=true` (staff, paginated) is the batched inventory read; its items also carry `product_name`/`product_sku`/`product_is_active` (`InventoryListItem`, product eager-loaded), and it takes repeatable `product_id` (max 100) and `search`; `GET /inventory/{product_id}` stays the public per-product read.
- **Database constraint errors**: `main.py` maps `sqlalchemy.exc.IntegrityError` to `409` (FK `23503`, unique `23505`) or `422` (CHECK `23514`, NOT NULL `23502`), with a `detail` naming the constraint and table, instead of a `500`. Services still validate first (an unknown product in `POST /orders` stays a friendly `404`); the handler covers what gets past them. `app/scripts/demo_rechazo.py` shows PostgreSQL rejecting an `order_items` row with a nonexistent product (`order_items_product_id_fkey`) and checks the rollback left nothing behind. Shipments carry two named CHECKs: `ck_shipments_in_transit_has_shipped_at` and `ck_shipments_delivered_has_delivered_at`.
- The initial Alembic migration (`2a6e6f24d115_initial_schema.py`) was hand-authored against no live DB. Every migration after it must use `--autogenerate` against a real database and be reviewed before committing. Admin-panel search (`search` on `GET /orders`, `/customers`, `/products`, `/inventory`) is `ILIKE '%text%'`, served by GIN `pg_trgm` indexes declared with `trigram_index()` (`app/db/base_class.py`); migration `5d8e1f2a9b47` creates the extension by hand (autogenerate doesn't), and `tests/conftest.py` creates it before `create_all`. Exception: autogenerate does not detect CHECK constraints (hand-written, e.g. `9c4e2a7b1d35_shipment_date_checks.py`; declare them in the model too, since tests build the schema with `create_all`) or Postgres enum value changes, so adding or removing an enum value needs a hand-written migration (pattern in `6bf0432e1cd9_remove_awaiting_payment_from_order_.py`: migrate affected rows, rename the old type, create the new one, `ALTER COLUMN ... TYPE ... USING col::text::new_type`, drop the old type). An enum change also touches `app/models/enums.py`, `API_CONTRACT.md` and the frontend mirrors in `front-end/services/*.py`.
- **Seeding** (`app/scripts/`, Fase 7): `seed_admin.py` creates the first admin from `FIRST_ADMIN_EMAIL`/`FIRST_ADMIN_PASSWORD`/`FIRST_ADMIN_FULL_NAME` env vars (idempotent, no-op if already set or vars unset — the only way to get an `employee`/`admin` account, no API endpoint for it). `seed_demo_data.py` creates demo categories/products with real stock (idempotent). Both run automatically on `api` container startup via `docker-compose.yml`.
- **Olist dataset** (`app/scripts/load_olist.py`, Momento 2, run by hand: `uv run python -m app.scripts.load_olist <csv_folder>`): ETL of the public Olist CSVs (stdlib `csv`, no pandas): `transform()` cleans/validates with no DB and counts rejections by reason; `save()` inserts in FK order with `INSERT ... ON CONFLICT DO NOTHING` and uuid5 ids, all in one transaction, so a second run inserts 0 rows. One `users` row per `customer_unique_id` (synthetic `olist-<hex>@mercadoexpress.com` email, unusable password `!`), products `is_active=False` (no names/photos: kept out of the storefront, still in the panel and reports) with an inventory row holding only what open orders reserve, Olist statuses mapped to the app's, plus payments (`BRL`), ledger `sale`/`reversal`, shipments and status history built the way the services would. An order with any rejected line is rejected whole. ~1.1M rows, ~3 min. `app/scripts/benchmark.py` measures HTTP latency (min/p50/p95/max) against a running API and `EXPLAIN ANALYZE` with/without `ix_orders_customer_id` / `ix_order_items_product_id` (`BEGIN; DROP INDEX; ...; ROLLBACK`), writing a Markdown report; its checkout orders are cancelled right after, so stock and net revenue are unchanged.

## front-end (Django)

Stack: Django, `httpx`, `django-environ`, whitenoise, gunicorn, pytest-django. Dependency management via `uv`.

```bash
cd front-end
uv sync
uv run manage.py migrate    # Django's own tables (sessions/admin) only — not business data
uv run manage.py runserver

uv run pytest                                    # full suite
uv run pytest tests/test_orders_service.py       # single file
uv run pytest apps/catalog/tests/                # per-app view tests
```

`conftest.py` forces `API_USE_MOCKS=True` for the whole test suite, so tests never need a real backend running. It also snapshots and restores the module-level `services/mock_data.py` collections around every test, because mock-mode services mutate them to imitate persistence — add any new mock collection to that fixture. `.env.example` defaults to `API_USE_MOCKS=False` for actual dev (calls the real backend at `MERCADOEXPRESS_API_BASE_URL`); flip to `API_USE_MOCKS=True` locally to work on UI without the backend up — this serves data from `services/mock_data.py` (demo user `cliente.demo@mercadoexpress.test` / `demo1234`).

### Architecture

```
templates/*  ->  apps/*/views.py  ->  services/*  ->  backend-api (HTTP)
```

- No view or template ever makes an HTTP call directly — everything goes through `services/`. When adding a feature that needs backend data, add/extend a `services/*.py` module first, matching a row in `API_CONTRACT.md`.
- `services/api_client.py` is the one generic HTTP client (one pooled `httpx.Client` per process, keep-alive across a page's calls); it centralizes error/timeout handling. Per-resource modules (`auth.py`, `customers.py`, `products.py` (categories too), `inventory.py`, `orders.py`, `payments.py`, `shipments.py`) wrap it. `reports.py` has no endpoint of its own: it composes the admin dashboard stats from the other modules (see the admin panel gaps below).
- `services/mock_data.py` exists only for the test suite — never reference it from production code paths.
- Apps: `core` (home, plus the shared `money` and `status_labels` template filters; API timestamps render through `money.py`'s `api_date`/`api_datetime`, which convert UTC to `TIME_ZONE`, never `|slice` on the raw string, or evening orders show tomorrow's date), `catalog` (categories/products, plus the wishlist — session state like the cart, no backend resource), `cart` (session-state only — not backend business logic), `accounts` (login/register/logout against the API), `dashboard` (authenticated profile/addresses), `orders` (checkout, history, tracking), `adminpanel` (staff panel at `/panel/`, see below).
- Catalog/product/order URLs key on the UUID `id` from the API, not a slug — the contract doesn't expose slugs.
- Checkout has no payment form: since the backend has no real payment gateway, the frontend implicitly uses `"card"` and calls `POST /orders/checkout` (`services/orders.py::checkout`), which saves the order, its items and the payment in one backend transaction. There is no half-created unpaid order to warn about.
- No automatic token-refresh flow is wired to views yet — access/refresh tokens simply expire and the user re-logs in.
- The user's role (`customer`/`employee`/`admin`) is cached in the session at login (`services/auth.py:save_role`/`is_staff`, populated from `GET /auth/me`) so staff-only views don't need an API call per request just to check it — see `apps/accounts/decorators.py:api_staff_required`.
- Staff (`employee`/`admin`) product management lives in `apps/catalog` (not a separate app): `/catalogo/admin/` to list/create/edit products plus upload/remove their images. No Django `Product` model — these views call `services/products.py`, which calls backend-api, same as every other catalog view.
- Everything else staff manage lives in `apps/adminpanel` at `/panel/` (every view `@api_staff_required`): dashboard stats, orders (manual status override plus shipment create/dispatch/deliver), categories CRUD, inventory (stock adjust, reorder level) and customers (list/detail). Its sidebar links to `/catalogo/admin/` for products rather than duplicating them. The status-override form only offers `services/orders.py::next_statuses(current)`, so staff can't pick a jump the backend would reject with `409`.
- The dashboard (`services/reports.py`) reads `GET /reports/summary` (net revenue as the headline), `GET /inventory?low_stock=true` (`services/inventory.py::list_inventory`) and `GET /orders?status=<stage>&page_size=5` per stage (paid, preparing, shipped); it does no aggregation of its own. `inventory_list` pages products 50 at a time and reads their stock in one `GET /inventory?product_id=...` call (`services/inventory.py::availability_by_product`), never one call per product; `?stock=bajo` lists low stock straight from `GET /inventory`; it includes inactive products (marked "Inactivo") via the staff-only `include_inactive=true` on `GET /products` / `GET /inventory`, and so does `/catalogo/admin/`. Every staff list paginates with numbered pages plus a jump field (`{% pagination page pages %}`, `apps/core/templatetags/pagination.py`) and filters server-side: orders by `status`/`search`/`created_from`/`created_to`, customers by `search`, products by `search`/`category_id`. `/panel/buscar/?q=` (the top bar search, `/` shortcut) shows orders, customers and products together. Order detail shows the status history; `/panel/inventario/<id>/historial/` shows a product's stock history.
- Storefront categories: visitors only ever see categories that have active products (`services/products.py::list_categories_with_products`, `GET /categories?with_products=true&sort=products`, fullest first, each with `active_product_count`; against an older backend without that field it counts active products itself). The home shows the first 3 with up to 4 products each (stock read per product shown), the navbar menu the first 8 plus "Ver todas las categorías", the catalog one collapsible list (sidebar on desktop, `<details>` on phones, opened by `static/js/modules/catalog-filter.js` on wide screens), and `/catalogo/categorias/` lists them all with a name filter. The home's "Así va un pedido" card is a CSS-only 14 s loop over the five real order states (labelled "Ejemplo"; it falls back to a plain list under `prefers-reduced-motion`). The customer's `/pedidos/` filters by status server-side and paginates.
- Inactive products: `GET /products` hides them from the public, but `GET /products/{id}` still returns them (with `is_active: false`) and `POST /orders` rejects them with `404`. The storefront therefore shows "No disponible" instead of the add-to-cart button, `cart:add` refuses them, and checkout sends the customer back to the cart if one was deactivated after being added.
- Status values (order/payment/shipment) stay in English on the wire, in querystrings, CSS classes (`status--pending`) and request bodies. Templates show them only through the `apps/core/templatetags/status_labels.py` filters (`order_status_label`, `payment_status_label`, `shipment_status_label`); the Spanish maps live in the matching `services/*.py`. Order and shipment statuses are separate vocabularies: the customer order page hides `shipment.status`, the admin panel shows it.
- UI copy is Spanish. Styling is split under `static/css/`: `tokens.css` (design tokens on `:root`, including the `--g0`..`--g10` green ramp), `base.css`, `components/*.css` (shared), `storefront/*.css` and `panel/*.css` (staff panel, "Boletín de precios" design: forest rail, hairline-ruled sheets, Archivo, a variation column). `base.html` links them in cascade order; `adminpanel/_layout.html` swaps the `styles` block for components + panel. Tokens (light "fresh market" palette: white surfaces on a pale-mint canvas, `--ink` = forest green text, `--volt` = action green, `--signal` = lime highlight; the old token names were kept on purpose. Bricolage Grotesque for display type and numbers, Figtree for body, loaded from Google Fonts in `base.html`) — reuse the tokens instead of hard-coding colors. The body is a full-height flex column with `<main>` taking the slack, which keeps the footer at the bottom on short pages; don't reintroduce fixed `min-height` hacks on `.page`. `static/js/app.js` is an ES module entry importing `static/js/modules/*.js` (vanilla JS, no build step); `static/js/panel.js` is panel-only. Design context for UI work lives in `front-end/PRODUCT.md` (product truth, pinned colour identity) and `front-end/DESIGN.md` (+ `.impeccable/design.json`, the panel's "Boletín de precios" system); read them before changing the panel's look. Confirmations never use the browser's native `confirm()`: a form adds `data-confirm="message"` (plus optional `data-confirm-title`, `data-confirm-ok`, `data-confirm-cancel`, `data-confirm-tone="danger"`; `{status}` in the text is replaced by the selected status option) and `app.js` opens the shared `<dialog>` from `templates/partials/confirm_dialog.html`.

## Cross-cutting API contract notes

- All money fields are decimal-as-string (2dp) in JSON — parse as `Decimal` on the Django side, never `float`.
- All IDs are UUIDv4 strings; timestamps are ISO 8601 UTC.
- Every error response is `{"detail": "..."}` (422 validation errors: `detail` is a list of field errors, not a string).
- List endpoints paginate via `page`/`page_size` query params, returning `{items, total, page, page_size, pages}` — except `/customers/me/addresses`, which is a flat unpaginated array (confirmed against the real backend, see `API_INTEGRATION_NOTES.md`).
- `GET /shipments/order/{id}` response shape is now confirmed: `{id, order_id, address_id, status, carrier, tracking_number, shipped_at, delivered_at, created_at, updated_at}`, `status` in `pending -> preparing -> in_transit -> delivered` (or `failed`/`returned`, or `cancelled` when the order is cancelled/refunded before dispatch). Same shape for the `POST` create/ship/deliver and `PATCH /shipments/{id}` responses.
- `GET /products` supports `search` (case-insensitive match on name or SKU) in addition to `category_id`/`page`/`page_size`. `services/products.list_products` sends it to the backend; only mock mode filters locally.
- Category responses carry `active_product_count` (products with `is_active=true`); `GET /categories` also takes `with_products=true` (count > 0) and `sort=products` (count desc, then name; default `name`). `Category.active_product_count` is a `query_expression`, not a column: `CategoryRepository` computes it with one outer-joined aggregate over active products (no N+1) and sets it with `set_committed_value`, not a `with_expression()` option, because `refresh()` re-runs an object's load options without the join and produced a cartesian product. `CategoryService` returns every category through `get_with_count`/`list_with_counts`.
- `GET /orders` also takes `search` (order number, customer email or name) and `created_from`/`created_to` (inclusive UTC dates); `GET /customers` takes `search` (name, email, phone). All filters combine with the existing ones.
- Order responses (`OrderOut`: create, get, list, status update) include `shipping_address`, the resolved address object (`null` if the order has none), next to the raw `shipping_address_id`, and `payments` (list of payment objects, `[]` while unpaid; eager-loaded in `OrderRepository`). Each item carries `product_name`/`product_sku` (`OrderItem.product` eager-loaded).
- Product responses (`GET`/list) include `images: [{id, url, position, created_at}]` (empty array if none). `url` is absolute and points at backend-api's own host (not the frontend's) — safe to use directly in `<img src>`. Managed only via `POST`/`DELETE /products/{id}/images`, never through `POST`/`PATCH /products`.

## Running both services together

```bash
docker compose -f backend-api/docker-compose.yml -f front-end/docker-compose.override.yml up --build
```

The `-f` order matters — Compose resolves relative build-context paths against the *first* `-f` file's directory. This brings up Postgres, FastAPI (`:8000`), Django (`:8080`), with Django reaching FastAPI at `http://api:8000` over the Docker network. Postgres listens on 5432 inside Docker but is published on host port `5433` (`POSTGRES_PORT` in `backend-api/.env`): host 5432 belongs to a native PostgreSQL service on this machine, which is not the project's database, and ports in Windows' dynamic range (49152-65535) can be reserved by Hyper-V after a reboot. There is no root-level compose file.

On this Windows host, hit services via `127.0.0.1:<port>`, not `localhost` — `localhost` resolves to IPv6 and the request hangs (Docker Desktop only binds IPv4). `127.0.0.1:8000/health` and `127.0.0.1:8080/` are the smoke-test URLs.

Staff-only actions (creating categories/products, adjusting inventory, managing shipments) need an `employee`/`admin` account — there's no self-service way to get one; use `seed_admin.py` (see above) to provision one for local testing. Once logged in as staff, products and their images are managed at `/catalogo/admin/`; everything else (dashboard, orders and shipments, categories, inventory, customers) is at `/panel/`.
