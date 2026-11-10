from django import template

from services.products import is_purchasable

register = template.Library()


@register.filter(name="in_wishlist")
def in_wishlist(product_id, wishlist):
    """Usage: {{ product.id|in_wishlist:wishlist }} -> True/False."""
    if wishlist is None:
        return False
    return wishlist.contains(product_id)


@register.filter(name="purchasable")
def purchasable(product):
    """Usage: {% if product|purchasable %} -- active and priced at or above the minimum."""
    return is_purchasable(product)
