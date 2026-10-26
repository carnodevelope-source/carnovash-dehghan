import time
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections

from apps.auth.models import CarWashFeaturePurchase
from apps.cloud_backup.service import backup_tenant, due


class Command(BaseCommand):
    help = 'Run tenant cloud backups outside web workers; --loop polls every minute.'

    def add_arguments(self, parser):
        parser.add_argument('--loop', action='store_true')
        parser.add_argument('--tenant', type=int)

    def handle(self, *args, **options):
        while True:
            try:
                close_old_connections()
                self.cycle(options)
            except Exception:
                # Even connection/metadata errors must not leak SQL or secrets.
                if not options['loop']:
                    raise CommandError('cloud_backup_cycle_failed') from None
                self.stderr.write('cloud_backup_cycle_failed')
            if not options['loop']:
                return
            time.sleep(60)

    def cycle(self, options):
        ids = CarWashFeaturePurchase.objects.filter(feature_key='cloud_storage', is_active=True)
        if options['tenant'] is not None:
            ids = ids.filter(tenant_id=options['tenant'])
        for tenant_id in ids.values_list('tenant_id', flat=True).iterator():
            if not due(tenant_id):
                continue
            run = backup_tenant(tenant_id, scheduled=True)
            if run:
                self.stdout.write(f'tenant={tenant_id} status={run.status} code={run.error_code}')
