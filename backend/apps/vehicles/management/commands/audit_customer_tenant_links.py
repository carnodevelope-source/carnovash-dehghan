"""Read-only audit. Deliberately has no --apply/--repair option."""
import json

from django.core.management.base import BaseCommand
from django.db.models import Count, F, Q
from apps.vehicles.models import CustomerProfile, VehicleEntry


class Command(BaseCommand):
    help = 'Report customer/vehicle tenant mismatches using counts and internal tenant IDs only.'

    def add_arguments(self, parser):
        parser.add_argument('--tenant', type=int, help='Limit to the vehicle tenant ID')
        parser.add_argument('--customer-id', type=int, help='Optional internal customer ID filter')

    def handle(self, *args, **options):
        vehicles = VehicleEntry.objects.filter(customer__isnull=False)
        if options['tenant'] is not None:
            vehicles = vehicles.filter(tenant_id=options['tenant'])
        if options['customer_id'] is not None:
            vehicles = vehicles.filter(customer_id=options['customer_id'])
        invalid = vehicles.filter(
            Q(tenant_id__isnull=True) | Q(customer__tenant_id__isnull=True)
            | ~Q(tenant_id=F('customer__tenant_id'))
        )
        groups = list(invalid.order_by().values('tenant_id', 'customer__tenant_id').annotate(vehicle_count=Count('pk')))
        quarantined = CustomerProfile.objects.filter(tenant_id__isnull=True)
        if options['customer_id'] is not None:
            quarantined = quarantined.filter(pk=options['customer_id'])
        self.stdout.write(json.dumps({
            'mode': 'report_only', 'mismatched_vehicle_count': invalid.count(),
            'groups': groups, 'quarantined_customer_count': quarantined.count(),
            'changed_records': 0,
        }))
