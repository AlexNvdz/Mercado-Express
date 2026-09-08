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

Key domain rules to know before touching orders/inventory/payments:

- **Auth**: single `users` table, `role` enum (`customer`/`employee`/`admin`) rather than per-role tables. No self-service staff/admin provisioning — those accounts are created directly in the DB.
- **Orders vs Sales**: `Order` is mutable lifecycle state (`pending -> awaiting_payment -> paid -> preparing -> shipped -> delivered`, with `cancelled`/`refunded` branches — see `API_CONTRACT.md` for the full transition table). `Sale` is an append-only record created once a payment completes — it's the immutable financial ledger, never edit it to fix an order.
- **Inventory**: single stock pool per product (`quantity_on_hand` / `quantity_reserved`; `quantity_available` is derived). Reserve/release/fulfill use `SELECT ... FOR UPDATE` row locks to prevent overselling under concurrent orders. Order creation is all-or-nothing — no partial stock reservation across items.
- **Payments/Shipments**: sit behind `PaymentGateway` / `ShipmentCarrier` provider abstractions with only a manual/placeholder implementation wired up (no real gateway or carrier yet, by design). `POST /payments` completes payment immediately via the manual gateway.
- The initial Alembic migration (`2a6e6f24d115_initial_schema.py`) was hand-authored against no live DB. Every migration after it must use `--autogenerate` against a real database and be reviewed before committing.
- **Seeding** (`app/scripts/`, Fase 7): `seed_admin.py` creates the first admin from `FIRST_ADMIN_EMAIL`/`FIRST_ADMIN_PASSWORD`/`FIRST_ADMIN_FULL_NAME` env vars (idempotent, no-op if already set or vars unset — the only way to get an `employee`/`admin` account, no API endpoint for it). `seed_demo_data.py` creates demo categories/products with real stock (idempotent). Both run automatically on `api` container startup via `docker-compose.yml`.

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

`conftest.py` forces `API_USE_MOCKS=True` for the whole test suite, so tests never need a real backend running. `.env.example` defaults to `API_USE_MOCKS=False` for actual dev (calls the real backend at `MERCADOEXPRESS_API_BASE_URL`); flip to `API_USE_MOCKS=True` locally to work on UI without the backend up — this serves data from `services/mock_data.py` (demo user `cliente.demo@mercadoexpress.test` / `demo1234`).

### Architecture

```
templates/*  ->  apps/*/views.py  ->  services/*  ->  backend-api (HTTP)
```

- No view or template ever makes an HTTP call directly — everything goes through `services/`. When adding a feature that needs backend data, add/extend a `services/*.py` module first, matching a row in `API_CONTRACT.md`.
- `services/api_client.py` is the one generic HTTP client (httpx-based); it centralizes error/timeout handling. Per-resource modules (`auth.py`, `customers.py`, `products.py`, `inventory.py`, `orders.py`, `payments.py`, `shipments.py`) wrap it.
- `services/mock_data.py` exists only for the test suite — never reference it from production code paths.
- Apps: `core` (home), `catalog` (categories/products), `cart` (session-state only — not backend business logic), `accounts` (login/register/logout against the API), `dashboard` (authenticated profile/addresses), `orders` (checkout, history, tracking).
- Catalog/product/order URLs key on the UUID `id` from the API, not a slug — the contract doesn't expose slugs.
- Checkout has no payment form: since the backend has no real payment gateway, the frontend implicitly uses `"card"` and calls `POST /payments` right after order creation.
- No automatic token-refresh flow is wired to views yet — access/refresh tokens simply expire and the user re-logs in.

## Cross-cutting API contract notes

- All money fields are decimal-as-string (2dp) in JSON — parse as `Decimal` on the Django side, never `float`.
- All IDs are UUIDv4 strings; timestamps are ISO 8601 UTC.
- Every error response is `{"detail": "..."}` (422 validation errors: `detail` is a list of field errors, not a string).
- List endpoints paginate via `page`/`page_size` query params, returning `{items, total, page, page_size, pages}` — except `/customers/me/addresses`, which is a flat unpaginated array (confirmed against the real backend, see `API_INTEGRATION_NOTES.md`).
- `GET /shipments/order/{id}` response shape is now confirmed: `{id, order_id, address_id, status, carrier, tracking_number, shipped_at, delivered_at, created_at, updated_at}`, `status` in `pending -> preparing -> in_transit -> delivered` (or `failed`/`returned`). Same shape for the `POST` create/ship/deliver responses.
- `GET /products` supports `search` (case-insensitive match on name or SKU) in addition to `category_id`/`page`/`page_size` — the frontend's navbar search in `services/products.list_products` predates this and may still be filtering client-side; check before assuming it uses the server-side param.

## Running both services together

```bash
docker compose -f backend-api/docker-compose.yml -f front-end/docker-compose.override.yml up --build
```

The `-f` order matters — Compose resolves relative build-context paths against the *first* `-f` file's directory. This brings up Postgres, FastAPI (`:8000`), Django (`:8080`), with Django reaching FastAPI at `http://api:8000` over the Docker network. There is no root-level compose file.

On this Windows host, hit services via `127.0.0.1:<port>`, not `localhost` — `localhost` resolves to IPv6 and the request hangs (Docker Desktop only binds IPv4). `127.0.0.1:8000/health` and `127.0.0.1:8080/` are the smoke-test URLs.

Staff-only actions (creating categories/products, adjusting inventory, managing shipments) need an `employee`/`admin` account — there's no self-service way to get one; use `seed_admin.py` (see above) to provision one for local testing.
