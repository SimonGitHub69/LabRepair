from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    label = "core"
    verbose_name = "Core"

    def ready(self):
        # Dopo autodiscover: riorganizza l'indice Admin come il menu LabRepair.
        from config.labrepair_admin import apply_labrepair_admin

        apply_labrepair_admin()
