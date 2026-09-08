def wishlist(request):
    """Exposes the current wishlist to every template as {{ wishlist }}."""
    return {"wishlist": getattr(request, "wishlist", None)}
