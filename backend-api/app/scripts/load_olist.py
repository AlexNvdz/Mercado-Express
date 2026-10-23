"""Olist dataset loader (ETL): CSV files -> clean -> validate -> save.

Run with: uv run python -m app.scripts.load_olist <csv_folder>

Reads the public Olist e-commerce dataset (olist_customers, olist_orders,
olist_order_items, olist_order_payments, olist_products and
product_category_name_translation CSVs) with the stdlib `csv` module and
loads it into the app's own tables, keeping the invariants the services keep
for orders created through the API:

- one `users` row (role customer, unusable password) per real person
  (`customer_unique_id`, not the per-order `customer_id`), and one
  `addresses` row per person + CEP/city/state;
- products inactive (the dataset has no names or photos, so they stay out of
  the public catalog but show in the panel and reports), priced at their
  latest sale price, uncategorized ones under "Sin clasificar", each with an
  inventory row holding exactly what its open orders reserve;
- orders with the Olist status mapped to the app's, lines grouped by product
  (uq_order_items_order_product), their payments, a `sale` ledger entry per
  paid order (plus its `reversal` if it was later cancelled), a shipment for
  shipped/delivered orders and the order status history.

Rejected rows are counted by reason. An order with any rejected line is
rejected whole (all-or-nothing, like POST /orders), and its lines and
payments with it.

Idempotent: every id is a uuid5 of the Olist id and rows go in with
INSERT ... ON CONFLICT DO NOTHING, so a second run inserts 0 new rows. The
whole save runs in one transaction: it is stored completely or not at all.
"""

import asyncio
import csv
import sys
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.asyncio_compat import apply_windows_event_loop_policy
from app.core.logging import configure_logging
from app.db.base import Base
from app.db.session import engine
from app.models.category import Category
from app.models.enums import (
    OrderStatus,
    OrderStatusChangeSource,
    PaymentStatus,
    SaleKind,
    ShipmentStatus,
    UserRole,
)

_NAMESPACE = uuid.UUID("6f1c3a52-2b8e-4f0e-9d4a-0b6c1e7f3a90")
_UNCATEGORIZED = "Sin clasificar"
_BATCH = 5000
# shortcut: Olist timestamps are Sao Paulo local time with no zone; read as a
# fixed UTC-03:00, so dates under the DST Brazil still had in 2016-2018 are an
# hour off. Use zoneinfo("America/Sao_Paulo") (needs tzdata on Windows) if
# that hour ever matters.
_BRT = timezone(timedelta(hours=-3))

_STATUS_MAP = {
    "created": OrderStatus.PENDING,
    "approved": OrderStatus.PAID,
    "invoiced": OrderStatus.PAID,
    "processing": OrderStatus.PREPARING,
    "shipped": OrderStatus.SHIPPED,
    "delivered": OrderStatus.DELIVERED,
    "canceled": OrderStatus.CANCELLED,
    "unavailable": OrderStatus.CANCELLED,
}
_PAID_STATUSES = {OrderStatus.PAID, OrderStatus.PREPARING, OrderStatus.SHIPPED, OrderStatus.DELIVERED}
# Stock still reserved, not yet fulfilled (fulfilment happens on dispatch).
_RESERVING_STATUSES = {OrderStatus.PENDING, OrderStatus.PAID, OrderStatus.PREPARING}

# Insert order (foreign keys first). Also the report order.
_TABLES = (
    "categories",
    "products",
    "inventory",
    "users",
    "addresses",
    "orders",
    "order_items",
    "payments",
    "sales",
    "shipments",
    "order_status_history",
)
# Built from other tables' rows, not read from a CSV of their own.
_DERIVED = {"categories", "inventory", "addresses", "sales", "shipments", "order_status_history"}


@dataclass
class TableLoad:
    read: int = 0
    rejected: Counter[str] = field(default_factory=Counter)
    rows: list[dict[str, Any]] = field(default_factory=list)
    inserted: int = 0


def _id(*parts: str) -> uuid.UUID:
    return uuid.uuid5(_NAMESPACE, ":".join(parts))


def _ts(value: str) -> datetime | None:
    """'' -> None; a bad format raises ValueError."""
    value = value.strip()
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=_BRT) if value else None


def _decimal(value: str) -> Decimal:
    """Raises ValueError/ArithmeticError if it is not a finite number."""
    number = Decimal(value.strip())
    if not number.is_finite():
        raise ValueError(value)
    return number


def _read(folder: Path, name: str) -> list[dict[str, str]]:
    with open(folder / name, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def transform(folder: Path) -> dict[str, TableLoad]:
    """Read, clean and validate the CSVs: every accepted row is ready to
    insert, every rejected one is counted under its reason. No database."""
    out = {name: TableLoad() for name in _TABLES}
    users, addresses, products, categories = (
        out["users"],
        out["addresses"],
        out["products"],
        out["categories"],
    )
    orders, order_items, payments = out["orders"], out["order_items"], out["payments"]

    # Customers -> users (one per person) + addresses.
    customers: dict[str, tuple[uuid.UUID, uuid.UUID]] = {}  # Olist customer_id -> (user id, address id)
    seen_addresses: set[uuid.UUID] = set()
    for row in _read(folder, "olist_customers_dataset.csv"):
        users.read += 1
        cid, person = row["customer_id"].strip(), row["customer_unique_id"].strip()
        cep, city, state = (
            row[k].strip() for k in ("customer_zip_code_prefix", "customer_city", "customer_state")
        )
        if not all((cid, person, cep, city, state)):
            users.rejected["campos obligatorios vacíos"] += 1
            continue
        if cid in customers:
            users.rejected["customer_id duplicado"] += 1
            continue
        user_id, address_id = _id("user", person), _id("address", person, cep, city, state)
        customers[cid] = (user_id, address_id)
        if address_id not in seen_addresses:
            seen_addresses.add(address_id)
            addresses.rows.append(
                {
                    "id": address_id,
                    "user_id": user_id,
                    "line1": f"CEP {cep}",
                    "city": city.title()[:120],
                    "state": state.upper()[:120],
                    "postal_code": cep[:20],
                    "country": "BR",
                }
            )
    seen_users: set[uuid.UUID] = set()
    for user_id, _ in customers.values():
        if user_id in seen_users:
            continue
        seen_users.add(user_id)
        users.rows.append(
            {
                "id": user_id,
                "email": f"olist-{user_id.hex}@mercadoexpress.com",
                # Not a bcrypt hash: verify_password() is always False, so
                # nobody can log in as an imported customer.
                "hashed_password": "!",
                "full_name": f"Cliente Olist {user_id.hex[:8]}",
                "role": UserRole.CUSTOMER,
                "is_active": True,
            }
        )

    order_rows = _read(folder, "olist_orders_dataset.csv")
    item_rows = _read(folder, "olist_order_items_dataset.csv")
    purchase_raw = {r["order_id"].strip(): r["order_purchase_timestamp"].strip() for r in order_rows}

    # Product price = its latest valid sale price (fixed-format timestamps
    # compare correctly as strings).
    prices: dict[str, tuple[str, Decimal]] = {}
    for item in item_rows:
        try:
            price = _decimal(item["price"])
        except (ValueError, ArithmeticError):
            continue
        pid, when = item["product_id"].strip(), purchase_raw.get(item["order_id"].strip(), "")
        if price > 0 and (pid not in prices or when >= prices[pid][0]):
            prices[pid] = (when, price)

    translations = {
        r["product_category_name"].strip(): r["product_category_name_english"].strip()
        for r in _read(folder, "product_category_name_translation.csv")
    }
    product_ids: dict[str, uuid.UUID] = {}
    category_sources: dict[str, str] = {}  # category name -> Olist name ('' for uncategorized)
    for row in _read(folder, "olist_products_dataset.csv"):
        products.read += 1
        pid, raw_category = row["product_id"].strip(), row["product_category_name"].strip()
        if not pid:
            products.rejected["product_id vacío"] += 1
            continue
        if pid in product_ids:
            products.rejected["product_id duplicado"] += 1
            continue
        if pid not in prices:
            products.rejected["sin precio de venta válido (nunca vendido)"] += 1
            continue
        if raw_category:
            category = (translations.get(raw_category) or raw_category).replace("_", " ").capitalize()
        else:
            category = _UNCATEGORIZED
        category_sources.setdefault(category, raw_category)
        product_ids[pid] = _id("product", pid)
        products.rows.append(
            {
                "id": product_ids[pid],
                "sku": f"OLIST-{pid}",
                "name": f"{category} {pid[:8]}",
                "description": f"Producto del dataset Olist ({pid}).",
                "category_id": _id("category", category),
                "price": prices[pid][1],
                "is_active": False,
            }
        )
    for category, raw_category in category_sources.items():
        categories.rows.append(
            {
                "id": _id("category", category),
                "name": category,
                "description": f"Categoría Olist '{raw_category}'."
                if raw_category
                else "Productos Olist sin categoría.",
                "is_active": True,
            }
        )

    # Lines grouped by (order, product); an order with a bad line is rejected whole.
    lines: dict[str, dict[str, list[Decimal]]] = defaultdict(lambda: defaultdict(list))
    freight: dict[str, Decimal] = defaultdict(Decimal)
    orders_with_bad_lines: set[str] = set()
    for item in item_rows:
        order_items.read += 1
        oid, pid = item["order_id"].strip(), item["product_id"].strip()
        reason = None
        if oid not in purchase_raw:
            reason = "línea de un pedido inexistente"
        elif pid not in product_ids:
            reason = "línea con producto inexistente"
        else:
            try:
                price, item_freight = _decimal(item["price"]), _decimal(item["freight_value"])
            except (ValueError, ArithmeticError):
                reason = "precio o flete no numérico"
            else:
                if price <= 0:
                    reason = "precio <= 0"
                elif item_freight < 0:
                    reason = "flete < 0"
        if reason:
            order_items.rejected[reason] += 1
            orders_with_bad_lines.add(oid)
            continue
        lines[oid][pid].append(price)
        freight[oid] += item_freight

    order_payments: dict[str, list[tuple[str, str, Decimal]]] = defaultdict(list)  # (sequential, type, value)
    seen_payments: set[tuple[str, str]] = set()
    for row in _read(folder, "olist_order_payments_dataset.csv"):
        payments.read += 1
        oid, seq = row["order_id"].strip(), row["payment_sequential"].strip()
        reason = None
        if oid not in purchase_raw:
            reason = "pago sin pedido"
        elif (oid, seq) in seen_payments:
            reason = "pago duplicado (order_id, payment_sequential)"
        else:
            try:
                value, installments = _decimal(row["payment_value"]), int(row["payment_installments"])
            except (ValueError, ArithmeticError):
                reason = "valor o cuotas no numéricos"
            else:
                if value <= 0:
                    reason = "valor <= 0"
                elif installments <= 0:
                    reason = "cuotas <= 0"
        if reason:
            payments.rejected[reason] += 1
            continue
        seen_payments.add((oid, seq))
        order_payments[oid].append((seq, row["payment_type"].strip(), value))

    reserved: Counter[str] = Counter()  # Olist product_id -> units reserved by open orders
    seen_orders: set[str] = set()
    for row in order_rows:
        orders.read += 1
        oid = row["order_id"].strip()
        status = _STATUS_MAP.get(row["order_status"].strip())
        purchased = approved = dispatched = delivered = None
        reason = None
        if oid in seen_orders:
            reason = "order_id duplicado"
        elif row["customer_id"].strip() not in customers:
            reason = "cliente inexistente o rechazado"
        elif status is None:
            reason = "estado desconocido"
        else:
            try:
                purchased, approved, dispatched, delivered = (
                    _ts(row[k])
                    for k in (
                        "order_purchase_timestamp",
                        "order_approved_at",
                        "order_delivered_carrier_date",
                        "order_delivered_customer_date",
                    )
                )
            except ValueError:
                reason = "fecha con formato inválido"
            else:
                if purchased is None:
                    reason = "sin fecha de compra"
                elif status == OrderStatus.DELIVERED and delivered is None:
                    reason = "entregado sin fecha de entrega"
                elif status in (OrderStatus.SHIPPED, OrderStatus.DELIVERED) and dispatched is None:
                    reason = "despachado sin fecha de despacho"
                elif dispatched is not None and dispatched < purchased:
                    reason = "despacho anterior a la compra"
                elif delivered is not None and dispatched is not None and delivered < dispatched:
                    reason = "entrega anterior al despacho"
                elif oid in orders_with_bad_lines:
                    reason = "detalle con líneas rechazadas"
                elif oid not in lines:
                    reason = "pedido sin detalle"
                elif status in _PAID_STATUSES and not order_payments.get(oid):
                    reason = "pagado sin pagos válidos"
        if reason:
            orders.rejected[reason] += 1
            if oid not in seen_orders:  # a duplicate's lines/payments belong to the first row
                rejected_lines = sum(len(p) for p in lines.get(oid, {}).values())
                if rejected_lines:
                    order_items.rejected["pedido rechazado"] += rejected_lines
                if order_payments.get(oid):
                    payments.rejected["pedido rechazado"] += len(order_payments[oid])
            seen_orders.add(oid)
            continue
        seen_orders.add(oid)
        assert status is not None and purchased is not None
        _add_order(
            out,
            oid,
            row,
            status,
            purchased,
            approved,
            dispatched,
            delivered,
            customers,
            product_ids,
            lines[oid],
            freight[oid],
            order_payments.get(oid, []),
            reserved,
        )

    for pid, product_id in product_ids.items():
        out["inventory"].rows.append(
            {
                "id": _id("inventory", pid),
                "product_id": product_id,
                # No stock data in Olist: on hand = what open orders reserve.
                "quantity_on_hand": reserved[pid],
                "quantity_reserved": reserved[pid],
                "reorder_level": 0,
            }
        )
    return out


def _add_order(
    out: dict[str, TableLoad],
    oid: str,
    row: dict[str, str],
    status: OrderStatus,
    purchased: datetime,
    approved: datetime | None,
    dispatched: datetime | None,
    delivered: datetime | None,
    customers: dict[str, tuple[uuid.UUID, uuid.UUID]],
    product_ids: dict[str, uuid.UUID],
    order_lines: dict[str, list[Decimal]],
    order_freight: Decimal,
    order_payments: list[tuple[str, str, Decimal]],
    reserved: Counter[str],
) -> None:
    """Rows of one accepted order: header, lines, payments, ledger,
    shipment and status history."""
    user_id, address_id = customers[row["customer_id"].strip()]
    order_id = _id("order", oid)
    subtotal = sum((sum(p, Decimal(0)) for p in order_lines.values()), Decimal(0))
    total = subtotal + order_freight
    last = max(d for d in (purchased, approved, dispatched, delivered) if d is not None)
    # Same rule as the app: an order is paid once a payment completed. A
    # cancelled Olist order counts as paid if it was approved with payments.
    paid = status in _PAID_STATUSES or (
        status == OrderStatus.CANCELLED and approved is not None and bool(order_payments)
    )
    paid_at = approved or purchased

    out["orders"].rows.append(
        {
            "id": order_id,
            "order_number": f"OL-{oid[:29].upper()}",
            "customer_id": user_id,
            "status": status,
            "subtotal": subtotal,
            "tax_amount": Decimal(0),
            "shipping_amount": order_freight,
            "total_amount": total,
            "shipping_address_id": address_id,
            "notes": f"Olist order_id {oid}",
            "created_at": purchased,
            "updated_at": last,
        }
    )
    for pid, unit_prices in order_lines.items():
        line_total = sum(unit_prices, Decimal(0))
        out["order_items"].rows.append(
            {
                "id": _id("order_item", oid, pid),
                "order_id": order_id,
                "product_id": product_ids[pid],
                "quantity": len(unit_prices),
                "unit_price": (line_total / len(unit_prices)).quantize(Decimal("0.01")),
                "line_total": line_total,
                "created_at": purchased,
                "updated_at": purchased,
            }
        )
        if status in _RESERVING_STATUSES:
            reserved[pid] += len(unit_prices)

    if paid:
        payment_status = PaymentStatus.COMPLETED
    else:
        payment_status = PaymentStatus.PENDING if status == OrderStatus.PENDING else PaymentStatus.CANCELLED
    for seq, method, value in order_payments:
        out["payments"].rows.append(
            {
                "id": _id("payment", oid, seq),
                "order_id": order_id,
                "amount": value,
                "currency": "BRL",
                "status": payment_status,
                "provider": "olist",
                "provider_reference": f"{oid}-{seq}"[:255],
                "method": method[:50] or None,
                "paid_at": paid_at if paid else None,
                "created_at": purchased,
                "updated_at": paid_at if paid else purchased,
            }
        )

    if paid:
        out["sales"].rows.append(
            {
                "id": _id("sale", oid),
                "order_id": order_id,
                "kind": SaleKind.SALE,
                "total_amount": total,
                "sold_at": paid_at,
            }
        )
        if status == OrderStatus.CANCELLED:
            out["sales"].rows.append(
                {
                    "id": _id("reversal", oid),
                    "order_id": order_id,
                    "kind": SaleKind.REVERSAL,
                    "total_amount": -total,
                    "sold_at": last,
                }
            )

    if status in (OrderStatus.SHIPPED, OrderStatus.DELIVERED):
        out["shipments"].rows.append(
            {
                "id": _id("shipment", oid),
                "order_id": order_id,
                "address_id": address_id,
                "status": ShipmentStatus.IN_TRANSIT
                if status == OrderStatus.SHIPPED
                else ShipmentStatus.DELIVERED,
                "carrier": "Olist",
                "tracking_number": None,
                "shipped_at": dispatched,
                "delivered_at": delivered if status == OrderStatus.DELIVERED else None,
                "created_at": dispatched,
                "updated_at": last,
            }
        )

    # The same steps the services record for an order that went through the API.
    source = OrderStatusChangeSource
    steps: list[
        tuple[OrderStatus | None, OrderStatus, OrderStatusChangeSource, uuid.UUID | None, datetime]
    ] = [(None, OrderStatus.PENDING, source.ORDER_CREATED, user_id, purchased)]
    if paid:
        steps.append((OrderStatus.PENDING, OrderStatus.PAID, source.PAYMENT, user_id, paid_at))
    if status == OrderStatus.PREPARING:
        steps.append((OrderStatus.PAID, OrderStatus.PREPARING, source.MANUAL, None, paid_at))
    if dispatched is not None and status in (OrderStatus.SHIPPED, OrderStatus.DELIVERED):
        steps.append((OrderStatus.PAID, OrderStatus.PREPARING, source.SHIPMENT_CREATED, None, dispatched))
        steps.append(
            (OrderStatus.PREPARING, OrderStatus.SHIPPED, source.SHIPMENT_DISPATCHED, None, dispatched)
        )
    if delivered is not None and status == OrderStatus.DELIVERED:
        steps.append((OrderStatus.SHIPPED, OrderStatus.DELIVERED, source.SHIPMENT_DELIVERED, None, delivered))
    if status == OrderStatus.CANCELLED:
        steps.append((steps[-1][1], OrderStatus.CANCELLED, source.MANUAL, None, last))
    for n, (from_status, to_status, change_source, actor_id, at) in enumerate(steps):
        out["order_status_history"].rows.append(
            {
                "id": _id("history", oid, str(n)),
                "order_id": order_id,
                "from_status": from_status,
                "to_status": to_status,
                "source": change_source,
                "actor_id": actor_id,
                # History is read ordered by created_at: +n microseconds keeps
                # steps that share an Olist timestamp in order.
                "created_at": at + timedelta(microseconds=n),
            }
        )


async def save(conn: AsyncConnection, tables: dict[str, TableLoad]) -> None:
    """INSERT ... ON CONFLICT DO NOTHING every accepted row, in foreign-key
    order, counting how many were actually new. Runs in `conn`'s
    transaction; the caller commits or rolls back."""
    for name, load in tables.items():
        if name == "products":
            await _resolve_category_ids(conn, tables)
        table = Base.metadata.tables[name]
        for start in range(0, len(load.rows), _BATCH):
            stmt = insert(table).on_conflict_do_nothing().returning(table.c.id)
            result = await conn.execute(stmt, load.rows[start : start + _BATCH])
            load.inserted += len(result.all())


async def _resolve_category_ids(conn: AsyncConnection, tables: dict[str, TableLoad]) -> None:
    """A category whose name already existed (unique) keeps its own id, not
    our uuid5: point the products at whatever id the name has now."""
    names = [row["name"] for row in tables["categories"].rows]
    result = await conn.execute(select(Category.id, Category.name).where(Category.name.in_(names)))
    real_ids = {_id("category", name): category_id for category_id, name in result.all()}
    for row in tables["products"].rows:
        row["category_id"] = real_ids[row["category_id"]]


def report(tables: dict[str, TableLoad]) -> str:
    header = (
        f"{'tabla':<22}{'leídos':>9}{'aceptados':>11}{'rechazados':>12}"
        f"{'a insertar':>12}{'nuevos':>9}{'ya existían':>13}"
    )
    out = [header, "-" * len(header)]
    for name, load in tables.items():
        rejected = sum(load.rejected.values())
        read, accepted = ("-", "-") if name in _DERIVED else (load.read, load.read - rejected)
        out.append(
            f"{name:<22}{read:>9}{accepted:>11}{rejected:>12}{len(load.rows):>12}"
            f"{load.inserted:>9}{len(load.rows) - load.inserted:>13}"
        )
        for reason, count in load.rejected.most_common():
            out.append(f"    rechazado: {reason}: {count}")
    return "\n".join(out)


async def load_olist(folder: Path) -> dict[str, TableLoad]:
    tables = transform(folder)
    async with engine.begin() as conn:
        await save(conn, tables)
    await engine.dispose()
    return tables


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: uv run python -m app.scripts.load_olist <csv_folder>")
    apply_windows_event_loop_policy()
    configure_logging()
    started = time.perf_counter()
    loaded = asyncio.run(load_olist(Path(sys.argv[1])))
    print(report(loaded))
    print(f"\nTiempo total: {time.perf_counter() - started:.1f} s")
