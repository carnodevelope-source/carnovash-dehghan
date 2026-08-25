import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection


def _int_setting(name, default, minimum=0):
    try:
        return max(minimum, int(os.environ.get(name) or default))
    except (TypeError, ValueError):
        return default


class Command(BaseCommand):
    help = 'Report the live database connection budget; this command never changes data.'

    def add_arguments(self, parser):
        parser.add_argument('--scheduler-connections', type=int, default=1)
        parser.add_argument('--maintenance-reserve', type=int, default=5)
        parser.add_argument('--admin-reserve', type=int, default=3)
        parser.add_argument('--json', action='store_true')

    def handle(self, *args, **options):
        workers = _int_setting('GUNICORN_WORKERS', 3, 1)
        threads = _int_setting('GUNICORN_THREADS', 24, 1)
        asgi_workers = _int_setting('ASGI_WORKERS', workers, 1)
        asgi_enabled = bool(getattr(settings, 'LIVE_ASGI_ENABLED', False))
        app_workers = asgi_workers if asgi_enabled else workers
        # Django connections are per process/thread in the worst case. This is
        # a conservative ceiling, not a promise of actual concurrent use.
        web_ceiling = app_workers * (1 if asgi_enabled else threads)
        reserve = max(0, options['scheduler_connections']) + max(0, options['maintenance_reserve']) + max(0, options['admin_reserve'])

        with connection.cursor() as cursor:
            cursor.execute('SELECT @@max_connections, @@sql_mode')
            max_connections, sql_mode = cursor.fetchone()
            cursor.execute("SHOW STATUS LIKE 'Threads_connected'")
            _name, connected = cursor.fetchone()

        safe_ceiling = max(0, int(max_connections) - reserve)
        report = {
            'database_max_connections': int(max_connections),
            'database_connected_now': int(connected),
            'sql_mode': sql_mode,
            'server_mode': 'asgi' if asgi_enabled else 'wsgi-gthread',
            'configured_workers': app_workers,
            'configured_threads': None if asgi_enabled else threads,
            'conservative_web_connection_ceiling': web_ceiling,
            'non_web_reserve': reserve,
            'safe_web_ceiling_after_reserve': safe_ceiling,
            'headroom_at_configured_ceiling': safe_ceiling - web_ceiling,
            'headroom_percent_at_configured_ceiling': round((safe_ceiling - web_ceiling) * 100 / max(1, int(max_connections)), 2),
            'decision': 'PASS' if web_ceiling <= safe_ceiling else 'FAIL_CONFIG_EXCEEDS_BUDGET',
        }
        output = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
        self.stdout.write(output)
        if report['decision'] != 'PASS':
            raise SystemExit(2)
