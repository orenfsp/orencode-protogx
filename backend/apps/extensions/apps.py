from django.apps import AppConfig


class ExtensionsConfig(AppConfig):
    name = "apps.extensions"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from . import (
            schema,  # noqa: F401
            signals,  # noqa: F401
        )
