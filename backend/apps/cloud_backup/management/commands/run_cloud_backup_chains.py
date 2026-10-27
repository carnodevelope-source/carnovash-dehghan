"""Explicit opt-in command; existing production scheduler is unchanged."""
import time
from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections
from django.utils import timezone
from apps.auth.models import CarWashFeaturePurchase
from apps.cloud_backup.models import BackupRun
from apps.cloud_backup.schedule import local_day, next_midnight
from apps.cloud_backup.scheduled_chain import execute_tenant, plan_tenant


def should_attempt(tenant_id, now):
    day = local_day(now)
    latest = BackupRun.objects.filter(tenant_id=tenant_id).order_by('-started_at', '-pk').first()
    if latest is None:
        return True
    success = BackupRun.objects.filter(tenant_id=tenant_id, status='success',
        recovery_status='integrity_verified').order_by('-started_at', '-pk').first()
    if success:
        recorded_day = success.scheduled_for or local_day(success.started_at)
        if recorded_day > day:
            return True  # Corrupt/future history must not suppress jobs indefinitely.
        if recorded_day == day:
            return False
    if latest.status in {'running', 'failed'}:
        failures = BackupRun.objects.filter(tenant_id=tenant_id, status='failed')
        if success:
            failures = failures.filter(started_at__gt=success.started_at)
        count = min(failures.count(), 9)
        return now >= (latest.finished_at or latest.started_at) + timedelta(seconds=min(21600, 60 * 2 ** count))
    return True


class Command(BaseCommand):
    help = 'Tehran midnight incremental chains; dry run unless --execute is supplied.'

    def add_arguments(self, parser):
        parser.add_argument('--tenant', type=int)
        parser.add_argument('--execute', action='store_true')
        parser.add_argument('--loop', action='store_true')
        parser.add_argument('--retention', action='store_true', help='Log, verify and apply approved 30-day chain retention')

    def handle(self, *args, **options):
        if options['loop'] and not options['execute']:
            raise CommandError('loop_requires_execute')
        while True:
            try:
                close_old_connections()
                self.cycle(options)
            except Exception:
                if not options['loop']:
                    raise CommandError('cloud_backup_cycle_failed') from None
                self.stderr.write('cloud_backup_cycle_failed')
            if not options['loop']:
                return
            # First attempt immediately after restart; daily identity and retry
            # backoff are persisted, so missed midnight resumes safely.
            now = timezone.now()
            time.sleep(max(0.05, min(30, (next_midnight(now) - now).total_seconds())))

    def cycle(self, options):
        from apps.cloud_backup.staging import cleanup_staging
        cleanup_staging()
        ids = CarWashFeaturePurchase.objects.filter(feature_key='cloud_storage', is_active=True)
        if options['tenant'] is not None:
            ids = ids.filter(tenant_id=options['tenant'])
        failed = False
        for tenant_id in ids.values_list('tenant_id', flat=True).distinct().iterator():
            now = timezone.now()
            if options['execute'] and not should_attempt(tenant_id, now):
                continue
            try:
                if not options['execute']:
                    plan, _, _ = plan_tenant(tenant_id, now)
                    self.stdout.write(f'tenant={tenant_id} action={plan.action} reason={plan.reason}')
                    continue
                run = execute_tenant(tenant_id, now)
                if run:
                    self.stdout.write(f'tenant={tenant_id} status={run.status} code={run.error_code}')
                    failed |= run.status != 'success'
                    if run.status == 'success' and options.get('retention'):
                        from apps.cloud_backup.automatic_retention import maintain_run
                        failed |= not maintain_run(run,output=self.stdout.write)
            except Exception:
                failed = True
                self.stderr.write(f'tenant={tenant_id} code=backup_failed')
        if failed:
            raise CommandError('cloud_backup_cycle_failed')
