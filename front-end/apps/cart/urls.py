from django.urls import path

from . import views

app_name = "cart"

urlpatterns = [
    path("", views.detail, name="detail"),
    path("agregar/<uuid:product_id>/", views.add, name="add"),
    path("actualizar/<uuid:product_id>/", views.update, name="update"),
    path("eliminar/<uuid:product_id>/", views.remove, name="remove"),
]
