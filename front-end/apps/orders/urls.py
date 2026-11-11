from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("", views.order_list, name="list"),
    path("checkout/", views.checkout, name="checkout"),
    path("reclamo/", views.claim_submit, name="claim"),
    path("reclamo/pedidos/", views.claim_orders, name="claim_orders"),
    path("<uuid:order_id>/", views.order_detail, name="detail"),
    path("<uuid:order_id>/cancelar/", views.order_cancel, name="cancel"),
    path("<uuid:order_id>/repetir/", views.order_reorder, name="reorder"),
]
