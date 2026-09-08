from .cart import Cart


class CartMiddleware:
    """Attaches request.cart (apps.cart.cart.Cart) to every request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.cart = Cart(request.session)
        return self.get_response(request)
