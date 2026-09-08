# MercadoExpress — Backend API

FastAPI + PostgreSQL REST API for MercadoExpress. Owns all business data
(customers, products, inventory, orders, payments, shipments, sales); the
Django frontend (`../front-end`) consumes it over HTTP — see
[`../API_CONTRACT.md`](../API_CONTRACT.md) for the full endpoint contract.

## Stack

Python 3.12 · FastAPI · SQLAlchemy 2.x (async, `psycopg[binary]` v3) ·
Alembic · Pydantic v2 / Pydantic Settings · PyJWT · pytest · Docker · Ruff · mypy.
Dependency management via [`uv`](https://docs.astral.sh/uv/).

## Project layout

```
app/
  core/         settings, logging, JWT/password hashing, Windows asyncio shim
  db/           SQLAlchemy engine/session, declarative base
  models/       ORM models (one file per entity) + shared enums
  schemas/      Pydantic request/response models
  repositories/ data-access layer (generic base + per-entity queries)
  services/     business logic / orchestration (order flow, auth, ...)
  routers/v1/   FastAPI routers, one per resource, aggregated in api.py
  dependencies.py  auth, role checks, pagination
  exceptions.py    domain exceptions -> HTTP status mapping (see main.py)
  main.py          app factory, middleware, exception handlers
alembic/        migrations (hand-authored initial schema in versions/)
tests/          pytest suite (real Postgres, transactional rollback per test)
```

## Local setup

Requires `uv` and a running PostgreSQL (via Docker Compose is easiest).

```bash
cp .env.example .env        # edit values as needed
uv sync                     # installs runtime + dev dependencies, creates .venv

# Start Postgres only (the `api` service in compose runs the container build instead)
docker compose up -d db

# Apply migrations
uv run alembic upgrade head

# Run the API with autoreload
uv run uvicorn app.main:app --reload
```

Swagger UI: http://localhost:8000/docs · Health check: http://localhost:8000/health

> **Windows note 1:** `.env.example` maps Postgres to host port `55432` (not
> the default 5432) because many dev machines already have a native
> PostgreSQL service bound to 5432. Adjust `POSTGRES_PORT` if that's not
> your situation.
>
> **Windows note 2:** always keep `--reload` when running uvicorn directly
> on Windows (outside Docker). psycopg3's async mode cannot use the default
> `ProactorEventLoop`; uvicorn only switches to a compatible loop when it
> spawns a reloader subprocess (i.e. with `--reload`, or `--workers > 1`).
> Without it you'll see `psycopg.InterfaceError: Psycopg cannot use the
> 'ProactorEventLoop'...`. This is Windows-only -- Docker (Linux) and macOS
> are unaffected.

## Tests

Tests run against a real PostgreSQL database (native types/constraints
matter here — UUID, native ENUM, CHECK constraints), in a dedicated
`mercadoexpress_test` database, with each test wrapped in a rolled-back
transaction for isolation.

```bash
# one-time: create the test database (same server as dev)
docker exec -e PGPASSWORD=<POSTGRES_PASSWORD> <db-container-name> \
  createdb -U <POSTGRES_USER> mercadoexpress_test

uv run pytest            # run the suite
uv run pytest --cov=app  # with coverage
```

## First admin account

There's no self-service "become admin" endpoint (registration always
creates a `customer`, by design — see API_CONTRACT.md). To get a working
admin account (needed for staff-only endpoints: create/edit
products/categories, adjust inventory, manage shipments):

```bash
# Set in .env (see .env.example): FIRST_ADMIN_EMAIL, FIRST_ADMIN_PASSWORD
uv run python -m app.scripts.seed_admin
```

Idempotent — safe to run repeatedly (skips if the account already exists;
promotes it to `admin` if it exists with a different role, never touches
its password). Docker Compose runs this automatically on `api` startup
(after migrations, before uvicorn) whenever `FIRST_ADMIN_EMAIL` /
`FIRST_ADMIN_PASSWORD` are set in `.env`.

## Migrations

```bash
uv run alembic revision --autogenerate -m "describe the change"  # needs a running DB
uv run alembic upgrade head
uv run alembic downgrade -1
```

The initial schema (`alembic/versions/2a6e6f24d115_initial_schema.py`) was
hand-authored (no DB was reachable at the time it was written); every
migration after it should use `--autogenerate` against a real database and
be reviewed before committing.

## Code quality

```bash
uv run ruff check .
uv run ruff format .
uv run mypy app
```

## Docker

```bash
docker compose up --build     # backend + Postgres
```

The `api` service runs `alembic upgrade head` before starting uvicorn. See
`docker-compose.yml` for details. This compose file is scoped to the backend
only; a root-level compose tying frontend + backend together can be added
later once that's needed (see `../API_CONTRACT.md` for the HTTP contract
the frontend integrates against in the meantime).

## Design notes

- **Auth**: single `users` table with a `role` enum (`customer`, `employee`,
  `admin`) rather than separate tables per role — adding a role later is a
  one-line enum change, see `app/dependencies.py::require_roles`.
- **Orders**: `Order` tracks mutable lifecycle state; `Sale` is an
  append-only record created once a payment completes, for clean
  analytics/reporting later.
- **Inventory**: single stock pool per product (`quantity_on_hand` /
  `quantity_reserved`), row-locked (`SELECT ... FOR UPDATE`) on
  reserve/release/fulfill so concurrent orders can't oversell. Multi-warehouse
  support would extend this table, not replace it.
- **Payments/Shipments**: both sit behind a small provider abstraction
  (`PaymentGateway`, `ShipmentCarrier`) with a manual/placeholder
  implementation — no real gateway or carrier is wired up yet, by design
  (see the task's Fase 5 scope).
