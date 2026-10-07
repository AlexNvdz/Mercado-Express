from django.db import models  # noqa: F401

# No models here by design -- see CLAUDE.md: Django never owns business data
# (customers, products, inventory, orders, payments, shipments, sales).
# This app is presentation-only; every view goes through services/*.py to
# backend-api, same as apps/catalog and apps/orders.
