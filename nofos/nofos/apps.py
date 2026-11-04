from django.apps import AppConfig


class NofosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "nofos"

    def ready(self):
        from . import history_index  # noqa: F401
        from . import metrics_signals  # noqa: F401
