"""Disposable test accounts, generated in memory; never production settings."""
import os
from django.conf import settings
from django.db import connections
from django.test.runner import DiscoverRunner
from apps.vehicles.db_permissions import statements
from apps.vehicles.mysql_guards import definer_user


class GuardMySQLRunner(DiscoverRunner):
    def setup_databases(self, **kwargs):
        suffix = os.urandom(5).hex()
        accounts = {role: {'USER': f'cw_{role}_{suffix}', 'PASSWORD': os.urandom(24).hex()}
                    for role in ('app', 'maint', 'restore')}
        settings.CUSTOMER_TENANT_GUARD_APP_ACCOUNT = accounts['app']['USER'] + '@%'
        settings.CUSTOMER_TENANT_TEST_ACCOUNTS = accounts
        with connections['default']._nodb_cursor() as cursor:
            for credentials in accounts.values():
                cursor.execute('CREATE USER %s@%s IDENTIFIED BY %s', [credentials['USER'], '%', credentials['PASSWORD']])
        self.guard_accounts = accounts
        self.guard_definers = []
        try:
            result = super().setup_databases(**kwargs)
            for alias in ('default', 'recovery'):
                connection = connections[alias]
                self.guard_definers.append(definer_user(connection.settings_dict['NAME']))
                roles = ('app', 'maint') if alias == 'default' else ('restore',)
                with connection.cursor() as cursor:
                    for role in roles:
                        for sql in statements(connection.settings_dict['NAME'], accounts[role]['USER'], '%', maintenance=role == 'maint'):
                            cursor.execute(sql)
            return result
        except Exception:
            self.cleanup_guard_accounts()
            raise

    def cleanup_guard_accounts(self):
        with connections['default']._nodb_cursor() as cursor:
            for credentials in self.guard_accounts.values():
                cursor.execute('DROP USER IF EXISTS %s@%s', [credentials['USER'], '%'])
            for user in self.guard_definers:
                cursor.execute('DROP USER IF EXISTS %s@%s', [user, 'localhost'])

    def teardown_databases(self, old_config, **kwargs):
        try:
            super().teardown_databases(old_config, **kwargs)
        finally:
            self.cleanup_guard_accounts()
