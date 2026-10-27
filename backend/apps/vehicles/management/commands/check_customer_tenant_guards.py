import json
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from apps.vehicles.mysql_guards import preflight, bodies, definer_grants, grant_rows, verify_existing


class Command(BaseCommand):
    help = 'Read-only deployment audit using the provisioning principal; no credentials printed.'

    def handle(self, *args, **options):
        if connection.vendor != 'mysql':
            raise CommandError('MySQL 8.4 guards are not installed on this database engine.')
        with connection.cursor() as cursor:
            database, user, existed = preflight(connection, cursor)
            current = verify_existing(cursor, database)
            if existed:
                actual_grants = {g.split(' TO ')[0] for g in grant_rows(cursor, (user, 'localhost'))
                                 if not g.startswith('GRANT USAGE ON *.* TO ')}
                if actual_grants != definer_grants(database):
                    raise CommandError('Guard definer grants are incomplete; keep writers stopped and retry installation.')
        if not existed or set(current) != set(bodies()):
            raise CommandError('Guard installation is incomplete; keep writers stopped and retry migration.')
        self.stdout.write(json.dumps({'status': 'verified', 'trigger_count': len(current),
                                     'app_grants': 'restricted', 'definer': 'locked'}))
