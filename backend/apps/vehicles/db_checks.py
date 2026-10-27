"""Check actual credentials, not just a claimed deployment principal."""
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.backends.signals import connection_created
from django.dispatch import receiver

from .mysql_guards import assert_restricted_grants, grant_rows


@receiver(connection_created, dispatch_uid='vehicles.check_tenant_guard_account')
def check_account(sender, connection, **kwargs):
    if connection.vendor != 'mysql':
        return
    role = getattr(settings, 'CUSTOMER_TENANT_GUARD_ROLE', 'application')
    if role == 'provisioning':
        # Explicit standalone migration process; this gives no DB privilege.
        return
    if role not in {'application', 'maintenance'}:
        raise ImproperlyConfigured('Unknown database process role.')
    try:
        with connection.cursor() as cursor:
            assert_restricted_grants(grant_rows(cursor), connection.settings_dict['NAME'], maintenance=role == 'maintenance', cursor=cursor)
    except Exception:
        # A rejected connection must not remain reusable after a caller catches
        # the configuration error. Reject every subsequent connection attempt.
        connection.close()
        raise
