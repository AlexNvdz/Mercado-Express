from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.product_list, name="list"),
    path("categoria/<uuid:category_id>/", views.product_list, name="category"),
    path("producto/<uuid:product_id>/", views.product_detail, name="detail"),
    path("producto/<uuid:product_id>/favorito/", views.wishlist_toggle, name="wishlist_toggle"),
    path("favoritos/", views.wishlist_view, name="wishlist"),
]
