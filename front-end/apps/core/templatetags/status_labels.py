"""Spanish display labels for the status vocabularies used across orders,
payments and shipments (see services/orders.py, services/payments.py,
services/shipments.py). The wire values (e.g. "preparing") stay in
English -- they're the API's vocabulary, reused in querystrings, CSS classes
and PATCH bodies -- these filters only translate what gets shown to a user.
"""

from django import template

from services.auth import USER_ROLE_LABELS
from services.inventory import INVENTORY_CHANGE_KIND_LABELS
from services.orders import ORDER_STATUS_LABELS, ORDER_STATUS_SOURCE_LABELS
from services.payments import PAYMENT_STATUS_LABELS
from services.shipments import SHIPMENT_STATUS_LABELS

register = template.Library()


@register.filter(name="order_status_label")
def order_status_label(value):
    return ORDER_STATUS_LABELS.get(value, value)


@register.filter(name="payment_status_label")
def payment_status_label(value):
    return PAYMENT_STATUS_LABELS.get(value, value)


@register.filter(name="shipment_status_label")
def shipment_status_label(value):
    return SHIPMENT_STATUS_LABELS.get(value, value)


@register.filter(name="order_status_source_label")
def order_status_source_label(value):
    return ORDER_STATUS_SOURCE_LABELS.get(value, value)


@register.filter(name="inventory_change_kind_label")
def inventory_change_kind_label(value):
    return INVENTORY_CHANGE_KIND_LABELS.get(value, value)


@register.filter(name="user_role_label")
def user_role_label(value):
    return USER_ROLE_LABELS.get(value, value)
