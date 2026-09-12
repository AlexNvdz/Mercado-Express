def wishlist(request):
    """Exposes the current wishlist to every template as {{ wishlist }}."""
    return {"wishlist": getattr(request, "wishlist", None)}


def nav_categories(request):
    """Exposes the category list to every template as {{ nav_categories }},
    so the navbar's category strip (templates/partials/navbar.html) doesn't
    need every view to remember to pass `categories` -- only core:home and
    catalog:list did before this existed. Swallows API errors so a flaky
    backend never takes down every page's navbar, just hides the strip.
    """
    from services import products
    from services.exceptions import ApiError

    try:
        return {"nav_categories": products.list_categories(page_size=8)["items"]}
    except ApiError:
        return {"nav_categories": []}
