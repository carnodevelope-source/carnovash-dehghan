import json
from django.core.management.base import BaseCommand, CommandError
from apps.cloud_backup.retention_service import retain_tenant

class Command(BaseCommand):
    help = 'Verified retention preview; deletion requires an explicitly reviewed token.'
    def add_arguments(self, parser):
        parser.add_argument('--tenant', type=int, required=True)
        parser.add_argument('--execute', action='store_true')
        parser.add_argument('--reviewed-token')
    def handle(self, *args, **options):
        try:
            result = retain_tenant(options['tenant'], execute=options['execute'],
                                   reviewed_token=options['reviewed_token'])
        except Exception:
            raise CommandError('retention_failed_no_unverified_deletion') from None
        self.stdout.write(json.dumps(result, sort_keys=True))
