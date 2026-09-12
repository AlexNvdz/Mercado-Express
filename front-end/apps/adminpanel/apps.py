from django.apps import AppConfig


class AdminpanelConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.adminpanel"
    label = "adminpanel"
    verbose_name = "Panel de administración"
