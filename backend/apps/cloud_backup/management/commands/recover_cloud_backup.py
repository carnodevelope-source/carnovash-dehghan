import os
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from apps.cloud_backup.archive import restore_fixture, verify


class Command(BaseCommand):
    help = 'Verify and recover an archive into a NEW private staging directory. Never restores default DB.'

    def add_arguments(self, parser):
        parser.add_argument('archive')
        parser.add_argument('--tenant', type=int, required=True)
        parser.add_argument('--output', required=True)
        parser.add_argument('--database', help='Optional isolated, migrated recovery database alias')

    def handle(self, *args, **options):
        output = Path(options['output'])
        try:
            # Authenticate and validate everything before writing any plaintext.
            verify(options['archive'], options['tenant'])
            output.mkdir(mode=0o700, parents=False, exist_ok=False)
            os.chmod(output, 0o700)
            verify(options['archive'], options['tenant'], output=output)
            if options['database']:
                restore_fixture(output / 'fixture.json', options['tenant'], options['database'])
        except Exception:
            raise CommandError('Recovery failed; inspect the private staging directory. No live database was restored.') from None
        self.stdout.write('Archive verified and recovered to private staging.')
