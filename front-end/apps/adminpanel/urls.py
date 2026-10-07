from django.urls import path

from . import views

app_name = "adminpanel"

urlpatterns = [
    path("", views.home, name="home"),
    # Orders: status overrides + shipment lifecycle (product CRUD lives at
    # catalog:admin_* already -- linked from the sidebar, not duplicated).
    path("pedidos/", views.orders_list, name="orders_list"),
    path("pedidos/<uuid:order_id>/", views.order_detail, name="order_detail"),
    path("pedidos/<uuid:order_id>/estado/", views.order_status_update, name="order_status_update"),
    path("pedidos/<uuid:order_id>/envio/crear/", views.shipment_create, name="shipment_create"),
    path("pedidos/<uuid:order_id>/envio/editar/", views.shipment_update, name="shipment_update"),
    path("pedidos/<uuid:order_id>/envio/despachar/", views.shipment_ship, name="shipment_ship"),
    path("pedidos/<uuid:order_id>/envio/entregar/", views.shipment_deliver, name="shipment_deliver"),
    # Categories
    path("categorias/", views.categories_list, name="categories_list"),
    path("categorias/nueva/", views.category_create, name="category_create"),
    path("categorias/<uuid:category_id>/", views.category_edit, name="category_edit"),
    path("categorias/<uuid:category_id>/eliminar/", views.category_delete, name="category_delete"),
    # Inventory
    path("inventario/", views.inventory_list, name="inventory_list"),
    path("inventario/<uuid:product_id>/ajustar/", views.inventory_adjust, name="inventory_adjust"),
    path("inventario/<uuid:product_id>/reorden/", views.inventory_set_reorder, name="inventory_set_reorder"),
    path("inventario/<uuid:product_id>/historial/", views.inventory_history, name="inventory_history"),
    # Customers
    path("clientes/", views.customers_list, name="customers_list"),
    path("clientes/<uuid:customer_id>/", views.customer_detail, name="customer_detail"),
]
