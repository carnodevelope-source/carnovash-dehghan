"""Generate only synthetic realtime rows for development/staging benchmarks."""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.realtime.models import LiveOutbox


class Command(BaseCommand):
    help = 'Create synthetic LiveOutbox rows in batches. Refuses production settings.'

    def add_arguments(self, parser):
        parser.add_argument('--tenant-id', required=True, type=int)
        parser.add_argument('--count', required=True, type=int)
        parser.add_argument('--batch-size', type=int, default=1000)
        parser.add_argument('--seed', default='benchmark')
        parser.add_argument('--allow-staging', action='store_true')

    def handle(self, *args, **options):
        if not settings.DEBUG and not options['allow_staging']:
            raise CommandError('Refusing non-debug execution. Pass --allow-staging only on an isolated staging database.')
        count = max(0, options['count'])
        batch_size = max(1, min(options['batch_size'], 5000))
        tenant_id = options['tenant_id']
        seed = str(options['seed'])
        created = 0
        while created < count:
            end = min(created + batch_size, count)
            LiveOutbox.objects.bulk_create([
                LiveOutbox(
                    tenant_id=tenant_id,
                    event_type='benchmark.updated',
                    entity_type='benchmark',
                    entity_id=f'{seed}-{index}',
                    payload={'tenant_id': tenant_id, 'benchmark': True, 'sequence': index},
                )
                for index in range(created, end)
            ], batch_size=batch_size)
            created = end
            self.stdout.write(f'Created {created}/{count} synthetic LiveOutbox rows.')
