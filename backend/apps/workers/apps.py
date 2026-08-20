from django.apps import AppConfig

class WorkersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.workers'

    def ready(self):
        from . import signals  # noqa: F401
