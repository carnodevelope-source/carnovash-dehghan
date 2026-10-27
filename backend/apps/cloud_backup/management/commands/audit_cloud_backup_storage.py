import json
from django.core.management.base import BaseCommand, CommandError
from apps.cloud_backup.storage_audit import audit_tenant

class Command(BaseCommand):
    help='Read-only encrypted full archive audit; never authorizes deletion.'
    def add_arguments(self,parser):
        parser.add_argument('--tenant',type=int,required=True)
    def handle(self,*args,**options):
        try:
            result=audit_tenant(options['tenant'])
        except Exception:
            raise CommandError('storage_audit_failed') from None
        self.stdout.write(json.dumps(result,sort_keys=True))
