import os
import stat
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from apps.cloud_backup.archive import restore_fixture, verify, recovery_guard


class Command(BaseCommand):
    help = 'Verify and recover an archive into a NEW private staging directory. Never restores default DB.'

    def add_arguments(self, parser):
        parser.add_argument('archive')
        parser.add_argument('--tenant', type=int, required=True)
        parser.add_argument('--output', required=True)
        parser.add_argument('--database', help='Optional isolated, migrated recovery database alias')
        parser.add_argument('--confirm-isolated-restore', action='store_true', help='Explicit operator approval for the recovery DB')

    def handle(self, *args, **options):
        output = Path(options['output'])
        try:
            if options['database']:
                if not options['confirm_isolated_restore']:
                    raise ValueError('recovery_confirmation_required')
                recovery_guard(options['database'])
            # Pin the same regular source file through both verification passes.
            fd = os.open(options['archive'], os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
            with os.fdopen(fd, 'rb') as source:
                if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                    raise ValueError('invalid_source')
                verify(source, options['tenant'])
                if output.absolute() != output.resolve():
                    raise ValueError('unsafe_output')
                output.mkdir(mode=0o700, parents=False, exist_ok=False)
                os.chmod(output, 0o700)
                verify(source, options['tenant'], output=output)
                if options['database']:
                    restore_fixture(output / 'fixture.json', options['tenant'], options['database'])
        except Exception:
            raise CommandError('Recovery failed; inspect the private staging directory. No live database was restored.') from None
        self.stdout.write('Archive verified and recovered to private staging.')
