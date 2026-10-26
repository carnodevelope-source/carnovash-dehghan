import json
import shutil
from datetime import timedelta
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.cloud_backup.models import BackupRun
from apps.cloud_backup.service import mount_guard, due


class Command(BaseCommand):
    help = 'Private operator-only backup status; no public download endpoint.'

    def add_arguments(self, parser):
        parser.add_argument('--tenant', type=int, required=True)

    def handle(self, *args, **options):
        runs = BackupRun.objects.filter(tenant_id=options['tenant']).order_by('-started_at')
        fields = ('started_at', 'finished_at', 'status', 'error_code', 'size_bytes', 'retained_bytes', 'verified_at', 'recovery_status')
        last_success = runs.filter(status='success').values(*fields).first()
        disk = {'mounted': False, 'free_bytes': None, 'total_bytes': None}
        try:
            mount_guard()
            usage = shutil.disk_usage(settings.CLOUD_BACKUP_MOUNT)
            disk.update(mounted=True, free_bytes=usage.free, total_bytes=usage.total)
        except Exception:
            pass
        self.stdout.write(json.dumps({
            'latest_attempt': runs.values(*fields).first(),
            'last_success': last_success,
            'success_is_stale': not last_success or not last_success['finished_at'] or last_success['finished_at'] < timezone.now() - timedelta(seconds=2 * settings.CLOUD_BACKUP_INTERVAL_SECONDS),
            'next_attempt_due': due(options['tenant']),
            'disk': disk,
        }, default=str))
