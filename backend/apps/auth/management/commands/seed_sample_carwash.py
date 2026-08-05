from django.core.management.base import BaseCommand, CommandError

from apps.auth.models import CarWash
from apps.auth.sample_tenant import (
    SAMPLE_MANAGER_PASSWORD,
    SAMPLE_MANAGER_PHONE,
    SAMPLE_MANAGER_USERNAME,
    SAMPLE_TENANT_NAME,
    create_or_refresh_sample_carwash,
    find_milan_source_tenant,
)


class Command(BaseCommand):
    help = (
        'Clone Milan carwash into sample demo tenant «کارنوواش نمونه» with masked historical PII. '
        'Manager: carnowash / carnowash@123'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--source-tenant-id',
            type=int,
            default=None,
            help='Source carwash id (defaults to Milan by name/slug).',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Delete and recreate existing sample tenant.',
        )

    def handle(self, *args, **options):
        source = None
        if options['source_tenant_id']:
            source = CarWash.objects.filter(pk=options['source_tenant_id']).first()
            if not source:
                raise CommandError(f'Source tenant id={options["source_tenant_id"]} not found.')
        else:
            source = find_milan_source_tenant()
            if not source:
                raise CommandError(
                    'Milan source tenant not found. Restore the backup into this DB first, '
                    'or pass --source-tenant-id.'
                )

        self.stdout.write(f'Source: id={source.id} name={source.name} slug={source.slug}')
        try:
            sample, manager = create_or_refresh_sample_carwash(
                source=source,
                force=bool(options['force']),
                stdout=self.stdout,
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(
            f'OK: {SAMPLE_TENANT_NAME} id={sample.id}\n'
            f'  login: {SAMPLE_MANAGER_USERNAME} / {SAMPLE_MANAGER_PASSWORD}\n'
            f'  phone: {SAMPLE_MANAGER_PHONE}\n'
            f'  manager_id: {manager.id}'
        ))
