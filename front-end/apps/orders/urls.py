from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("", views.order_list, name="list"),
    path("checkout/", views.checkout, name="checkout"),
    path("<uuid:order_id>/", views.order_detail, name="detail"),
    path("<uuid:order_id>/cancelar/", views.order_cancel, name="cancel"),
]
