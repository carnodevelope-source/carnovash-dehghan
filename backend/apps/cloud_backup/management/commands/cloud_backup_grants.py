"""Print reviewed table-level SQL; never connects to or modifies MySQL."""
import re

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from apps.cloud_backup.snapshot import ownership_registry, GLOBAL, TENANT, CHILDREN


class Command(BaseCommand):
    help = 'Print least-privilege GRANT statements, without password or execution.'

    def add_arguments(self, parser):
        parser.add_argument('--database-name', required=True)
        parser.add_argument('--user', default='carvash_backup')
        parser.add_argument('--host', default='%')

    def handle(self, *args, **options):
        for option in ('database_name', 'user', 'host'):
            if not re.fullmatch(r'[A-Za-z0-9_%.-]+', options[option]):
                raise CommandError('Invalid SQL identifier')
        ownership_registry()
        db, user, host = options['database_name'], options['user'], options['host']
        # User M2M privileges are stripped before serialization, so no auth-group
        # tables, session tables, technical outbox or HQ bulk-job SELECT is needed.
        tables = sorted({apps.get_model(label)._meta.db_table for label in TENANT | GLOBAL | set(CHILDREN) | {'cw_auth.carwash'}})
        for table in tables:
            self.stdout.write(f"GRANT SELECT ON `{db}`.`{table}` TO '{user}'@'{host}';")
        table = apps.get_model('cloud_backup.BackupRun')._meta.db_table
        self.stdout.write(f"GRANT SELECT, INSERT, UPDATE ON `{db}`.`{table}` TO '{user}'@'{host}';")
