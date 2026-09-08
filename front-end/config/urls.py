"""
URL configuration for the MercadoExpress frontend project.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
    path("catalogo/", include("apps.catalog.urls")),
    path("carrito/", include("apps.cart.urls")),
    path("cuenta/", include("apps.accounts.urls")),
    path("mi-cuenta/", include("apps.dashboard.urls")),
    path("pedidos/", include("apps.orders.urls")),
]
