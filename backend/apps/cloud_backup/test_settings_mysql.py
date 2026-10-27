"""Opt-in, disposable MySQL tests. NEVER point these settings at a live server."""
import os
from django.core.exceptions import ImproperlyConfigured
from .test_settings import *  # noqa: F403

if os.environ.get('CLOUD_BACKUP_TEST_MYSQL') != 'isolated':
    raise ImproperlyConfigured('Explicit isolated MySQL test opt-in required')

DATABASES = {
    alias: {
        'ENGINE': 'apps.vehicles.tests.mysql',
        'HOST': os.environ.get('CLOUD_BACKUP_TEST_DB_HOST', 'carvash-backup-review-mysql'),
        'PORT': '3306',
        'USER': 'root',
        'PASSWORD': '',  # Disposable network-isolated test instance only.
        'NAME': f'cloud_backup_{alias}',
        'OPTIONS': {'charset': 'utf8mb4'},
    }
    for alias in ('default', 'recovery')
}

TEST_RUNNER = 'apps.vehicles.tests.mysql_runner.GuardMySQLRunner'

# Test DBA is used only for schema/fixtures; repair uses generated restricted credentials.
CUSTOMER_TENANT_GUARD_ROLE = 'provisioning'
