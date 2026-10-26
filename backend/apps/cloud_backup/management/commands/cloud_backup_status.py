import json
from django.core.management.base import BaseCommand
from apps.cloud_backup.models import BackupRun


class Command(BaseCommand):
    help = 'Private operator-only backup status; no public download endpoint.'

    def add_arguments(self, parser):
        parser.add_argument('--tenant', type=int, required=True)

    def handle(self, *args, **options):
        runs = BackupRun.objects.filter(tenant_id=options['tenant']).order_by('-started_at')
        fields = ('started_at', 'finished_at', 'status', 'error_code', 'size_bytes', 'retained_bytes', 'verified_at', 'recovery_status')
        self.stdout.write(json.dumps({
            'latest_attempt': runs.values(*fields).first(),
            'last_success': runs.filter(status='success').values(*fields).first(),
        }, default=str))
