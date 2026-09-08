from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.profile, name="home"),
    path("perfil/", views.profile, name="profile"),
    path("direcciones/", views.address_list, name="addresses"),
    path("direcciones/nueva/", views.address_add, name="address_add"),
    path("direcciones/<uuid:address_id>/eliminar/", views.address_delete, name="address_delete"),
]
