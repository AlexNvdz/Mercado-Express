"""
Session-backed wishlist ("favoritos").

Like apps.cart.cart.Cart, this is pure frontend/presentation state -- which
products a visitor starred -- not business data, so it's fine for Django to
own it directly in the session rather than going through the backend API
(which has no wishlist endpoint in API_CONTRACT.md). Product details are
always re-fetched from services.products when rendering.
"""

from __future__ import annotations

from services import products

SESSION_KEY = "wishlist"


class Wishlist:
    def __init__(self, session):
        self.session = session
        ids = session.get(SESSION_KEY)
        if ids is None:
            ids = []
            session[SESSION_KEY] = ids
        self.ids: list[str] = ids

    def toggle(self, product_id: str) -> bool:
        """Returns True if the product ended up favorited, False if removed."""
        key = str(product_id)
        if key in self.ids:
            self.ids.remove(key)
            favorited = False
        else:
            self.ids.append(key)
            favorited = True
        self._save()
        return favorited

    def contains(self, product_id: str) -> bool:
        return str(product_id) in self.ids

    def _save(self) -> None:
        self.session[SESSION_KEY] = self.ids
        if hasattr(self.session, "modified"):
            self.session.modified = True

    def __len__(self) -> int:
        return len(self.ids)

    def __iter__(self):
        """Yield the favorited products still available in the catalog."""
        for product_id in self.ids:
            product = products.get_product(product_id)
            if product is not None:
                yield product
