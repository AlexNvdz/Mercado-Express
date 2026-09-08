from django import template

register = template.Library()


@register.filter(name="in_wishlist")
def in_wishlist(product_id, wishlist):
    """Usage: {{ product.id|in_wishlist:wishlist }} -> True/False."""
    if wishlist is None:
        return False
    return wishlist.contains(product_id)
