import json
from django.conf import settings
from django.core.management.base import BaseCommand
from apps.cloud_backup.service import consistent_read, eligible
from apps.cloud_backup.snapshot import SnapshotError, collect


class Command(BaseCommand):
    help = 'Read-only tenant snapshot diagnosis; prints only counts, sizes and schema labels.'

    def add_arguments(self, parser):
        parser.add_argument('--tenant', type=int, required=True)

    def handle(self, *args, **options):
        result = {'mode': 'report_only', 'limits': {
            'rows': settings.CLOUD_BACKUP_MAX_ROWS,
            'fixture_bytes': settings.CLOUD_BACKUP_MAX_JSON_BYTES,
            'files': settings.CLOUD_BACKUP_MAX_FILES,
            'field_length': settings.CLOUD_BACKUP_MAX_FIELD_BYTES,
        }}
        try:
            result['eligible'] = eligible(options['tenant'])
            with consistent_read():
                fixture, files = collect(options['tenant'])
            result.update(status='ok', fixture_bytes=len(fixture), files=len(files))
        except SnapshotError as exc:
            result.update(status='blocked', code=str(exc), diagnostics=exc.diagnostics)
        except Exception:
            result.update(status='failed', code='diagnostic_failed')
        self.stdout.write(json.dumps(result))
