"""Olist ETL (app/scripts/load_olist.py) on a tiny hand-made dataset that
has one row for each rejection rule."""

import csv
from decimal import Decimal
from pathlib import Path

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import Inventory
from app.models.order import Order
from app.models.sale import Sale
from app.models.shipment import Shipment
from app.scripts.load_olist import _id, save, transform

_DATASET: dict[str, list[list[str]]] = {
    "olist_customers_dataset.csv": [
        ["customer_id", "customer_unique_id", "customer_zip_code_prefix", "customer_city", "customer_state"],
        ["c1", "person1", "01001", "sao paulo", "SP"],
        ["c2", "person1", "01001", "sao paulo", "SP"],  # same person, second order
        ["c3", "person2", "20000", "rio de janeiro", "RJ"],
        ["c4", "person3", "", "niteroi", "RJ"],  # rejected: empty CEP
    ],
    "olist_products_dataset.csv": [
        ["product_id", "product_category_name"],
        ["p1", "beleza_saude"],
        ["p2", ""],  # -> "Sin clasificar"
        ["p3", "pc_gamer"],  # rejected: never sold, no price
    ],
    "product_category_name_translation.csv": [
        ["product_category_name", "product_category_name_english"],
        ["beleza_saude", "health_beauty"],
    ],
    "olist_orders_dataset.csv": [
        [
            "order_id",
            "customer_id",
            "order_status",
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
        ],
        [
            "o1",
            "c1",
            "delivered",
            "2018-01-01 10:00:00",
            "2018-01-01 11:00:00",
            "2018-01-02 10:00:00",
            "2018-01-05 10:00:00",
        ],
        ["o2", "c2", "invoiced", "2018-02-01 10:00:00", "2018-02-01 11:00:00", "", ""],
        ["o3", "c3", "canceled", "2018-03-01 10:00:00", "2018-03-01 11:00:00", "", ""],
        ["o4", "c3", "delivered", "2018-04-01 10:00:00", "2018-04-01 11:00:00", "2018-04-02 10:00:00", ""],
        ["o5", "c3", "created", "2018-05-01 10:00:00", "", "", ""],  # no lines
        ["o6", "c1", "processing", "2018-06-01 10:00:00", "2018-06-01 11:00:00", "", ""],  # bad line
    ],
    "olist_order_items_dataset.csv": [
        ["order_id", "order_item_id", "product_id", "price", "freight_value"],
        ["o1", "1", "p1", "10.00", "1.00"],
        ["o1", "2", "p1", "10.00", "1.00"],  # same product: grouped into quantity 2
        ["o1", "3", "p2", "5.00", "2.00"],
        ["o2", "1", "p1", "12.00", "0.00"],
        ["o3", "1", "p2", "5.00", "0.00"],
        ["o4", "1", "p1", "11.00", "0.00"],  # latest p1 sale (April): p1 costs 11.00
        ["o6", "1", "pX", "10.00", "0.00"],  # product that does not exist
        ["oZ", "1", "p1", "10.00", "0.00"],  # order that does not exist
    ],
    "olist_order_payments_dataset.csv": [
        ["order_id", "payment_sequential", "payment_type", "payment_installments", "payment_value"],
        ["o1", "1", "credit_card", "3", "29.00"],
        ["o1", "2", "credit_card", "0", "1.00"],  # rejected: 0 installments
        ["o2", "1", "voucher", "1", "0.00"],  # rejected: value 0
        ["o2", "2", "boleto", "1", "12.00"],
        ["o3", "1", "credit_card", "1", "5.00"],
        ["o4", "1", "credit_card", "1", "10.00"],
        ["oZ", "1", "credit_card", "1", "3.00"],  # order that does not exist
    ],
}


def _write_dataset(folder: Path) -> Path:
    for name, rows in _DATASET.items():
        with open(folder / name, "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerows(rows)
    return folder


def test_transform_counts_and_rejection_reasons(tmp_path: Path) -> None:
    tables = transform(_write_dataset(tmp_path))

    counts = {name: (load.read, dict(load.rejected), len(load.rows)) for name, load in tables.items()}
    assert counts["users"] == (4, {"campos obligatorios vacíos": 1}, 2)
    assert counts["addresses"][2] == 2
    assert counts["products"] == (3, {"sin precio de venta válido (nunca vendido)": 1}, 2)
    assert sorted(row["name"] for row in tables["categories"].rows) == ["Health beauty", "Sin clasificar"]
    assert counts["orders"] == (
        6,
        {"entregado sin fecha de entrega": 1, "pedido sin detalle": 1, "detalle con líneas rechazadas": 1},
        3,
    )
    assert counts["order_items"] == (
        8,
        {"línea con producto inexistente": 1, "línea de un pedido inexistente": 1, "pedido rechazado": 1},
        4,
    )
    assert counts["payments"] == (
        7,
        {"cuotas <= 0": 1, "valor <= 0": 1, "pago sin pedido": 1, "pedido rechazado": 1},
        3,
    )
    # o1 and o2 paid; o3 paid and then cancelled -> sale + reversal.
    assert sorted((row["kind"].value, row["total_amount"]) for row in tables["sales"].rows) == [
        ("reversal", Decimal("-5.00")),
        ("sale", Decimal("5.00")),
        ("sale", Decimal("12.00")),
        ("sale", Decimal("29.00")),
    ]
    assert len(tables["shipments"].rows) == 1  # only o1 (delivered)
    assert len(tables["order_status_history"].rows) == 5 + 2 + 3  # o1, o2, o3
    assert {row["price"] for row in tables["products"].rows} == {Decimal("11.00"), Decimal("5.00")}


async def test_save_is_idempotent_and_keeps_app_invariants(
    db_session: AsyncSession, admin_client: AsyncClient, tmp_path: Path
) -> None:
    folder = _write_dataset(tmp_path)
    conn = await db_session.connection()

    first = transform(folder)
    await save(conn, first)
    assert all(load.inserted == len(load.rows) for load in first.values())

    second = transform(folder)
    await save(conn, second)
    assert {name: load.inserted for name, load in second.items()} == dict.fromkeys(second, 0)

    o1 = await db_session.scalar(select(Order).where(Order.id == _id("order", "o1")))
    assert o1 is not None
    assert (o1.status, o1.subtotal, o1.shipping_amount, o1.total_amount) == (
        "delivered",
        Decimal("25.00"),
        Decimal("4.00"),
        Decimal("29.00"),
    )
    shipment = await db_session.scalar(select(Shipment).where(Shipment.order_id == o1.id))
    assert shipment is not None and shipment.delivered_at is not None
    # o2 is paid, not dispatched: its unit of p1 is still reserved.
    p1_stock = await db_session.scalar(select(Inventory).where(Inventory.product_id == _id("product", "p1")))
    assert p1_stock is not None
    assert (p1_stock.quantity_on_hand, p1_stock.quantity_reserved) == (1, 1)
    assert await db_session.scalar(select(func.sum(Sale.total_amount))) == Decimal("41.00")  # 29 + 12 + 5 - 5

    # Loaded orders read back through the API like any other.
    resp = await admin_client.get(f"/api/v1/orders/{o1.id}")
    assert resp.status_code == 200
    assert [
        (i["quantity"], i["line_total"]) for i in sorted(resp.json()["items"], key=lambda i: i["quantity"])
    ] == [
        (1, "5.00"),
        (2, "20.00"),
    ]
    assert [p["amount"] for p in resp.json()["payments"]] == ["29.00"]
    history = (await admin_client.get(f"/api/v1/orders/{o1.id}/history")).json()
    assert [h["to_status"] for h in history] == ["pending", "paid", "preparing", "shipped", "delivered"]
