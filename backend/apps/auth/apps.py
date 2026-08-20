from django.apps import AppConfig


class AuthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.auth'
    label = 'cw_auth'
    verbose_name = 'Authentication'

    def ready(self):
        from .scheduler import start_internal_scheduler
        from . import signals  # noqa: F401

        start_internal_scheduler()
