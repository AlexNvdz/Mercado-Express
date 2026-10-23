"""Performance benchmark: HTTP latency per endpoint + EXPLAIN ANALYZE with
and without an index. Writes the results to a Markdown file.

Run against a running API and its database (read from .env, like the app):
    uv run python -m app.scripts.benchmark --base-url http://127.0.0.1:8000 --out benchmark_results.md

Needs a staff account (--email/--password, default FIRST_ADMIN_EMAIL /
FIRST_ADMIN_PASSWORD) and an active product with available stock.

1. HTTP latency: N timed requests per endpoint after one warm-up request,
   reported as min/p50/p95/max in ms (client-side wall time, httpx).
   POST /orders/checkout writes real rows (order, payment, sale), so it
   registers its own throwaway customer and each order it creates is
   cancelled right after, untimed, through PATCH /orders/{id}/status: that
   releases the stock and appends the ledger reversal, so stock and net
   revenue end where they started.
2. EXPLAIN ANALYZE of "orders of a customer" (ix_orders_customer_id) and
   "best-selling products" / "sales of one product"
   (ix_order_items_product_id), first as is and then inside
   BEGIN; DROP INDEX ...; EXPLAIN ANALYZE ...; ROLLBACK -- the schema is
   never changed. DROP INDEX holds an exclusive lock on the table until the
   rollback (a few ms), so other requests to that table wait meanwhile.
"""

import argparse
import asyncio
import re
import statistics
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.asyncio_compat import apply_windows_event_loop_policy
from app.core.config import settings
from app.db.session import engine


def _stats(ms: list[float]) -> tuple[float, float, float, float]:
    p95 = statistics.quantiles(ms, n=100, method="inclusive")[94]
    return min(ms), statistics.median(ms), p95, max(ms)


def _login(client: httpx.Client, email: str, password: str) -> dict[str, str]:
    resp = client.post("/auth/login", data={"username": email, "password": password})
    resp.raise_for_status()
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _http_benchmark(
    base_url: str, email: str, password: str, n: int, search: str
) -> list[tuple[str, list[float]]]:
    with httpx.Client(base_url=base_url.rstrip("/") + settings.API_V1_PREFIX, timeout=60) as client:
        staff = _login(client, email, password)
        customer_email = f"bench-{uuid.uuid4().hex[:10]}@mercadoexpress.com"
        client.post(
            "/auth/register",
            json={"email": customer_email, "password": "Bench12345", "full_name": "Benchmark"},
        ).raise_for_status()
        customer = _login(client, customer_email, "Bench12345")

        orders = client.get("/orders", params={"page": 1}, headers=staff).json()["items"]
        if not orders:
            raise SystemExit("No orders in the database: load data first.")
        stock = client.get("/inventory", params={"page_size": 100}, headers=staff).json()["items"]
        product_id = next((row["product_id"] for row in stock if row["quantity_available"] >= 1), None)
        if product_id is None:
            raise SystemExit("No active product with available stock for the checkout benchmark.")
        # Inputs for the admin panel's lookups: one page of products (as the
        # inventory screen sends them), an order number and a customer email.
        page_ids = [
            p["id"]
            for p in client.get(
                "/products", params={"include_inactive": "true", "page_size": 50}, headers=staff
            ).json()["items"]
        ]
        order_term = orders[-1]["order_number"][3:11].lower()
        customers = client.get("/customers", params={"page_size": 1}, headers=staff).json()["items"]
        customer_term = customers[0]["email"].split("@")[0][:12]

        def checkout() -> httpx.Response:
            return client.post(
                "/orders/checkout",
                json={"items": [{"product_id": product_id, "quantity": 1}], "method": "card"},
                headers=customer,
            )

        def cancel(resp: httpx.Response) -> None:
            order_id = resp.json()["id"]
            client.patch(
                f"/orders/{order_id}/status", json={"status": "cancelled"}, headers=staff
            ).raise_for_status()

        cases = [
            ("GET /products (público)", lambda: client.get("/products"), None),
            (
                "GET /products?include_inactive=true (staff)",
                lambda: client.get("/products", params={"include_inactive": "true"}, headers=staff),
                None,
            ),
            (
                f"GET /products?search={search}&include_inactive=true (staff)",
                lambda: client.get(
                    "/products", params={"search": search, "include_inactive": "true"}, headers=staff
                ),
                None,
            ),
            (
                "GET /orders/{id} (staff)",
                lambda: client.get(f"/orders/{orders[0]['id']}", headers=staff),
                None,
            ),
            (
                "GET /orders?page=1 (staff)",
                lambda: client.get("/orders", params={"page": 1}, headers=staff),
                None,
            ),
            (
                f"GET /orders?search={order_term} (staff)",
                lambda: client.get("/orders", params={"search": order_term}, headers=staff),
                None,
            ),
            (
                f"GET /customers?search={customer_term} (staff)",
                lambda: client.get("/customers", params={"search": customer_term}, headers=staff),
                None,
            ),
            (
                f"GET /inventory?product_id=x{len(page_ids)}&include_inactive=true (staff)",
                lambda: client.get(
                    "/inventory",
                    params={"product_id": page_ids, "include_inactive": "true", "page_size": 100},
                    headers=staff,
                ),
                None,
            ),
            ("GET /reports/summary (staff)", lambda: client.get("/reports/summary", headers=staff), None),
            (
                "GET /inventory?low_stock=true (staff)",
                lambda: client.get("/inventory", params={"low_stock": "true"}, headers=staff),
                None,
            ),
            ("POST /orders/checkout (cliente)", checkout, cancel),
        ]
        results = []
        for label, call, after in cases:
            timings = []
            for i in range(n + 1):
                started = time.perf_counter()
                resp = call()
                elapsed = (time.perf_counter() - started) * 1000
                resp.raise_for_status()
                if after is not None:
                    after(resp)
                if i > 0:  # request 0 is the warm-up
                    timings.append(elapsed)
            results.append((label, timings))
            print(f"{label}: p50 {statistics.median(timings):.1f} ms")
        return results


# (title, index, sql, ms with index, plan with index, ms without, plan without)
_PlanResult = tuple[str, str, str, float, str, float, str]
_EXECUTION_TIME = re.compile(r"Execution Time: ([\d.]+) ms")


async def _plan(conn: AsyncConnection, sql: str) -> tuple[float, str]:
    await conn.execute(text(f"EXPLAIN ANALYZE {sql}"))  # warm-up: same buffers for both runs
    rows = (await conn.execute(text(f"EXPLAIN ANALYZE {sql}"))).scalars().all()
    plan = "\n".join(rows)
    match = _EXECUTION_TIME.search(plan)
    return float(match.group(1)) if match else float("nan"), plan


async def _explain_benchmark() -> list[_PlanResult]:
    async with engine.connect() as conn:
        await conn.execute(text("ANALYZE orders, order_items"))
        await conn.commit()
        customer_id = (
            await conn.execute(
                text("SELECT customer_id FROM orders GROUP BY 1 ORDER BY count(*) DESC LIMIT 1")
            )
        ).scalar_one()
        product_id = (
            await conn.execute(
                text("SELECT product_id FROM order_items GROUP BY 1 ORDER BY count(*) DESC LIMIT 1")
            )
        ).scalar_one()
        await conn.rollback()
        # Literal UUIDs read from our own tables (EXPLAIN takes no bind parameters).
        queries = [
            (
                "Pedidos de un cliente",
                "ix_orders_customer_id",
                "SELECT id, order_number, status, total_amount, created_at FROM orders "
                f"WHERE customer_id = '{uuid.UUID(str(customer_id))}' ORDER BY created_at DESC LIMIT 20",
            ),
            (
                "Ventas de un producto",
                "ix_order_items_product_id",
                "SELECT order_id, quantity, line_total FROM order_items "
                f"WHERE product_id = '{uuid.UUID(str(product_id))}'",
            ),
            (
                "Productos más vendidos (top 10)",
                "ix_order_items_product_id",
                "SELECT product_id, sum(quantity) AS units FROM order_items "
                "GROUP BY product_id ORDER BY units DESC LIMIT 10",
            ),
        ]
        results = []
        for title, index, sql in queries:
            with_ms, with_plan = await _plan(conn, sql)
            await conn.rollback()
            await conn.execute(text(f"DROP INDEX {index}"))
            without_ms, without_plan = await _plan(conn, sql)
            await conn.rollback()  # the index is back
            results.append((title, index, sql, with_ms, with_plan, without_ms, without_plan))
            print(f"{title}: con índice {with_ms:.3f} ms, sin índice {without_ms:.3f} ms")
    await engine.dispose()
    return results


def _markdown(base_url: str, n: int, http: list[tuple[str, list[float]]], plans: list[_PlanResult]) -> str:
    out = [
        "# Benchmark MercadoExpress",
        "",
        f"Fecha: {datetime.now(UTC):%Y-%m-%d %H:%M} UTC. API: {base_url}. N = {n} peticiones por endpoint "
        "(más 1 de calentamiento, no medida). Tiempo de pared medido en el cliente (httpx).",
        "",
        "## Latencia HTTP (ms)",
        "",
        "| Endpoint | min | p50 | p95 | max |",
        "|---|---:|---:|---:|---:|",
    ]
    for label, timings in http:
        low, p50, p95, high = _stats(timings)
        out.append(f"| `{label}` | {low:.1f} | {p50:.1f} | {p95:.1f} | {high:.1f} |")
    out += ["", "## EXPLAIN ANALYZE con y sin índice", ""]
    out += ["| Consulta | Índice | Con índice (ms) | Sin índice (ms) |", "|---|---|---:|---:|"]
    for title, index, _sql, with_ms, _wp, without_ms, _np in plans:
        out.append(f"| {title} | `{index}` | {with_ms:.3f} | {without_ms:.3f} |")
    for title, index, sql, with_ms, with_plan, without_ms, without_plan in plans:
        out += [
            "",
            f"### {title}",
            "",
            f"```sql\n{sql};\n```",
            "",
            f"Con `{index}` ({with_ms:.3f} ms):",
            "",
            f"```\n{with_plan}\n```",
            "",
            f"Sin `{index}` (BEGIN; DROP INDEX; EXPLAIN ANALYZE; ROLLBACK) ({without_ms:.3f} ms):",
            "",
            f"```\n{without_plan}\n```",
        ]
    return "\n".join(out) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--email", default=settings.FIRST_ADMIN_EMAIL)
    parser.add_argument("--password", default=settings.FIRST_ADMIN_PASSWORD)
    parser.add_argument("-n", type=int, default=50)
    parser.add_argument("--search", default="health")
    parser.add_argument("--out", type=Path, default=Path("benchmark_results.md"))
    args = parser.parse_args()
    if not args.email or not args.password:
        parser.error("staff credentials needed: --email/--password or FIRST_ADMIN_EMAIL/FIRST_ADMIN_PASSWORD")

    http = _http_benchmark(args.base_url, args.email, args.password, args.n, args.search)
    apply_windows_event_loop_policy()
    plans = asyncio.run(_explain_benchmark())
    args.out.write_text(_markdown(args.base_url, args.n, http, plans), encoding="utf-8")
    print(f"Resultados en {args.out.resolve()}")


if __name__ == "__main__":
    main()
