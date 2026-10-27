from django.core.management.base import BaseCommand
from apps.vehicles.db_permissions import statements


class Command(BaseCommand):
    help = 'Print table-scoped SQL for EXISTING fresh accounts; no credentials or execution.'

    def add_arguments(self, parser):
        parser.add_argument('--database-name', required=True)
        parser.add_argument('--user', required=True)
        parser.add_argument('--host', default='%')
        parser.add_argument('--maintenance', action='store_true')

    def handle(self, *args, **options):
        for sql in statements(options['database_name'], options['user'], options['host'], maintenance=options['maintenance']):
            self.stdout.write(sql)
