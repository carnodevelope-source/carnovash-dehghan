"""Explicit standalone maintenance process only. Never load in the web worker."""
import os
from django.core.exceptions import ImproperlyConfigured
from config.settings import *  # noqa: F403

if not os.environ.get('CUSTOMER_REPAIR_DB_USER') or not os.environ.get('CUSTOMER_REPAIR_DB_PASSWORD'):
    raise ImproperlyConfigured('Inject dedicated maintenance credentials using a secret store.')
DATABASES['default'] = dict(DATABASES['default'], USER=os.environ['CUSTOMER_REPAIR_DB_USER'],
                            PASSWORD=os.environ['CUSTOMER_REPAIR_DB_PASSWORD'])

CUSTOMER_TENANT_GUARD_ROLE = 'maintenance'
