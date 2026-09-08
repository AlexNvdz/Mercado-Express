def cart(request):
    """Exposes the current cart to every template as {{ cart }}."""
    return {"cart": getattr(request, "cart", None)}
