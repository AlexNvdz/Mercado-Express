"""Idempotent demo catalog seed: a handful of categories and products, each
with real stock, so the order -> payment -> shipment flow can actually be
exercised end to end without needing to hand-create data through the admin
API first.

Run with: uv run python -m app.scripts.seed_demo_data

Safe to run repeatedly: skips any category/product whose name/SKU already
exists rather than duplicating or overwriting it. Not wired into
docker-compose automatically (unlike seed_admin) -- this is sample data,
not something every environment should get for free; run it manually when
you want a populated catalog (e.g. for frontend integration testing).
"""

import asyncio
import logging

from app.core.asyncio_compat import apply_windows_event_loop_policy
from app.core.logging import configure_logging
from app.db.session import AsyncSessionLocal
from app.models.category import Category
from app.models.inventory import Inventory
from app.models.product import Product
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_repository import ProductRepository

logger = logging.getLogger(__name__)

# (category name, category description, [(sku, product name, description, price, initial stock), ...])
DEMO_CATALOG: list[tuple[str, str, list[tuple[str, str, str, str, int]]]] = [
    (
        "Electronics",
        "Phones, computers and gadgets",
        [
            ("ELEC-001", "Wireless Mouse", "2.4GHz wireless mouse, USB receiver", "19.99", 100),
            ("ELEC-002", "Mechanical Keyboard", "RGB backlit mechanical keyboard", "59.99", 50),
            ("ELEC-003", "USB-C Hub", "7-in-1 USB-C hub with HDMI", "34.99", 75),
        ],
    ),
    (
        "Home & Kitchen",
        "Everyday home and kitchen essentials",
        [
            ("HOME-001", "Ceramic Mug Set", "Set of 4 ceramic mugs, 350ml", "24.99", 60),
            ("HOME-002", "Stainless Steel Knife Set", "6-piece kitchen knife set", "44.99", 30),
        ],
    ),
    (
        "Books",
        "Fiction and non-fiction",
        [
            ("BOOK-001", "The Pragmatic Programmer", "Software craftsmanship classic", "39.99", 40),
            ("BOOK-002", "Clean Code", "A handbook of agile software craftsmanship", "42.99", 40),
        ],
    ),
]


async def seed_demo_data() -> None:
    async with AsyncSessionLocal() as session:
        categories = CategoryRepository(session)
        products = ProductRepository(session)

        created_categories = 0
        created_products = 0

        for cat_name, cat_description, product_specs in DEMO_CATALOG:
            category = await categories.get_by_name(cat_name)
            if category is None:
                category = Category(name=cat_name, description=cat_description, is_active=True)
                session.add(category)
                await session.flush()
                created_categories += 1
                logger.info("Created category %s", cat_name)

            for sku, name, description, price, stock in product_specs:
                product = await products.get_by_sku(sku)
                if product is not None:
                    continue
                product = Product(
                    sku=sku,
                    name=name,
                    description=description,
                    category_id=category.id,
                    price=price,
                    is_active=True,
                )
                session.add(product)
                await session.flush()
                session.add(
                    Inventory(product_id=product.id, quantity_on_hand=stock, quantity_reserved=0)
                )
                created_products += 1
                logger.info("Created product %s (%s) with %d units in stock", sku, name, stock)

        await session.commit()
        logger.info(
            "Demo catalog seed done: %d categories, %d products created (rest already existed).",
            created_categories,
            created_products,
        )


if __name__ == "__main__":
    apply_windows_event_loop_policy()
    configure_logging()
    asyncio.run(seed_demo_data())
