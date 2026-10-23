"""Demo: the database itself rejects an order line whose product does not exist.

Run with: uv run python -m app.scripts.demo_rechazo

OrderService would answer 404 before touching the database, so this skips
it: inside one transaction it creates a throwaway customer and order, then
adds an `order_items` row straight through the ORM with a random
product_id. PostgreSQL rejects the INSERT with a foreign key violation
(SQLSTATE 23503). The script prints the constraint name, rolls back, and
checks in a new session that nothing (customer, order or line) was saved.

Over HTTP the same error becomes a 409 with the constraint name in `detail`
(the IntegrityError handler in app/main.py).
"""

import asyncio
import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.asyncio_compat import apply_windows_event_loop_policy
from app.db.session import AsyncSessionLocal, engine
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.user import User


async def demo_rechazo(session_factory: async_sessionmaker[AsyncSession] = AsyncSessionLocal) -> str:
    """Returns the name of the constraint that rejected the line."""
    tag = uuid.uuid4().hex[:10]
    missing_product_id = uuid.uuid4()
    async with session_factory() as session:
        user = User(
            email=f"demo-rechazo-{tag}@mercadoexpress.com", hashed_password="!", full_name="Demo rechazo"
        )
        session.add(user)
        await session.flush()
        order = Order(order_number=f"DEMO-{tag}", customer_id=user.id)
        session.add(order)
        await session.flush()
        print(f"Pedido de prueba {order.order_number} creado (sin confirmar) en la transacción.")
        print(f"Insertando order_items con product_id={missing_product_id}, que no existe en products...")
        session.add(
            OrderItem(
                order_id=order.id,
                product_id=missing_product_id,
                quantity=1,
                unit_price=Decimal("1.00"),
                line_total=Decimal("1.00"),
            )
        )
        try:
            await session.flush()
        except IntegrityError as exc:
            diag = exc.orig.diag  # type: ignore[union-attr]
            sqlstate = exc.orig.sqlstate  # type: ignore[union-attr]
            constraint = diag.constraint_name
            print(f"RECHAZADO por PostgreSQL: SQLSTATE {sqlstate}, llave foránea '{constraint}'")
            print(f"  tabla: {diag.table_name}; detalle: {diag.message_detail}")
            await session.rollback()
            print("ROLLBACK hecho.")
        else:
            await session.rollback()
            raise AssertionError("PostgreSQL accepted a line with a nonexistent product.")

    async with session_factory() as check:
        saved = await check.execute(
            select(
                select(func.count()).select_from(User).where(User.email.like(f"%{tag}%")).scalar_subquery(),
                select(func.count())
                .select_from(Order)
                .where(Order.order_number == f"DEMO-{tag}")
                .scalar_subquery(),
                select(func.count())
                .select_from(OrderItem)
                .where(OrderItem.product_id == missing_product_id)
                .scalar_subquery(),
            )
        )
        users, orders, items = saved.one()
    assert (users, orders, items) == (0, 0, 0), f"Something was saved: {users=} {orders=} {items=}"
    print("Verificado en una sesión nueva: 0 clientes, 0 pedidos y 0 líneas guardados.")
    assert constraint is not None
    return str(constraint)


async def _main() -> None:
    await demo_rechazo()
    await engine.dispose()


if __name__ == "__main__":
    apply_windows_event_loop_policy()
    asyncio.run(_main())
