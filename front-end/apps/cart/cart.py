"""
Session-backed shopping cart.

The cart itself is pure frontend state (product_id -> quantity) kept in the
Django session -- this is presentation state, not business data, so it is
fine for Django to own it directly. Product details/prices are always
re-fetched from services.products so the cart never trusts stale client-side
prices. Order creation (services.orders.create_order) is what turns this
into a real, priced order on the backend.
"""

from __future__ import annotations

from decimal import Decimal

from services import products

SESSION_KEY = "cart"


class Cart:
    def __init__(self, session):
        self.session = session
        cart = session.get(SESSION_KEY)
        if cart is None:
            cart = {}
            session[SESSION_KEY] = cart
        self.cart: dict[str, int] = cart

    def add(self, product_id: str, quantity: int = 1) -> None:
        key = str(product_id)
        self.cart[key] = self.cart.get(key, 0) + quantity
        if self.cart[key] <= 0:
            self.cart.pop(key, None)
        self._save()

    def update(self, product_id: str, quantity: int) -> None:
        key = str(product_id)
        if quantity <= 0:
            self.cart.pop(key, None)
        else:
            self.cart[key] = quantity
        self._save()

    def remove(self, product_id: str) -> None:
        self.cart.pop(str(product_id), None)
        self._save()

    def clear(self) -> None:
        self.cart.clear()
        self._save()

    def _save(self) -> None:
        self.session[SESSION_KEY] = self.cart
        # Plain dicts (used in unit tests) don't have this flag; real Django
        # sessions do, and need it set to persist the mutated cart dict.
        if hasattr(self.session, "modified"):
            self.session.modified = True

    def __len__(self) -> int:
        return sum(self.cart.values())

    def __iter__(self):
        """Yield enriched line items: product data + quantity + subtotal."""
        for product_id, quantity in self.cart.items():
            product = products.get_product(product_id)
            if product is None:
                continue
            price = Decimal(str(product["price"]))
            yield {
                "product": product,
                "quantity": quantity,
                "unit_price": price,
                "subtotal": price * quantity,
            }

    def get_total(self) -> Decimal:
        return sum((item["subtotal"] for item in self), Decimal("0"))

    def as_order_items(self) -> list[dict]:
        return [{"product_id": pid, "quantity": qty} for pid, qty in self.cart.items()]
