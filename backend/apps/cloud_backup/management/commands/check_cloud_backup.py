import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from apps.cloud_backup.archive import key
from apps.cloud_backup.service import pinned_root, write_guard
from apps.cloud_backup.snapshot import ownership_registry


class Command(BaseCommand):
    help = 'Read-only mount/UID/key/schema preflight; does not create backup directories.'

    def handle(self, *args, **options):
        try:
            ownership_registry()
            key()
            with pinned_root():
                write_guard()
            if not Path(settings.MEDIA_ROOT).is_dir() or not os.access(settings.MEDIA_ROOT, os.R_OK | os.X_OK):
                raise ValueError('media_access_failed')
        except Exception:
            raise CommandError('cloud_backup_preflight_failed') from None
        self.stdout.write(f'cloud_backup_preflight_ok uid={os.geteuid()} gid={os.getegid()}')
