from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.product_list, name="list"),
    path("categoria/<uuid:category_id>/", views.product_list, name="category"),
    path("producto/<uuid:product_id>/", views.product_detail, name="detail"),
    path("producto/<uuid:product_id>/favorito/", views.wishlist_toggle, name="wishlist_toggle"),
    path("favoritos/", views.wishlist_view, name="wishlist"),
    # Staff-only product management (see apps/accounts/decorators.py:api_staff_required)
    path("admin/", views.product_admin_list, name="admin_list"),
    path("admin/nuevo/", views.product_admin_create, name="admin_create"),
    path("admin/<uuid:product_id>/", views.product_admin_edit, name="admin_edit"),
    path("admin/<uuid:product_id>/eliminar/", views.product_admin_delete, name="admin_delete"),
    path(
        "admin/<uuid:product_id>/imagenes/subir/",
        views.product_admin_upload_image,
        name="admin_upload_image",
    ),
    path(
        "admin/<uuid:product_id>/imagenes/<uuid:image_id>/eliminar/",
        views.product_admin_delete_image,
        name="admin_delete_image",
    ),
]
