from .wishlist import Wishlist


class WishlistMiddleware:
    """Attaches request.wishlist (apps.catalog.wishlist.Wishlist) to every request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.wishlist = Wishlist(request.session)
        return self.get_response(request)
