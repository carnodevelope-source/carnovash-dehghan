from django.core.management.base import BaseCommand

from apps.auth.models import CarWash
from apps.auth.models import User
from apps.inventory.models import InventoryItem, StockMovement
from apps.notifications.models import NotificationLog
from apps.payments.models import CashflowTransaction, Payment, Wallet
from apps.products.models import Product, ProductCategory
from apps.reports.models import ReportSnapshot
from apps.services.models import GeneralSettings, Service, ServiceCategory
from apps.vehicles.models import (
    CustomerProfile,
    VehicleEntry,
    VehicleJob,
    VehicleJobProduct,
    VehicleJobService,
    VehicleStatusLog,
)
from apps.workers.models import WorkerAttendance, WorkerProfile


class Command(BaseCommand):
    help = 'Backfill tenant for existing rows using a default tenant.'

    def handle(self, *args, **options):
        tenant, _ = CarWash.objects.get_or_create(slug='default', defaults={'name': 'Default CarWash'})

        User.objects.filter(tenant__isnull=True).update(tenant=tenant)

        WorkerProfile.objects.filter(tenant__isnull=True).update(tenant=tenant)
        WorkerAttendance.objects.filter(tenant__isnull=True).update(tenant=tenant)

        ServiceCategory.objects.filter(tenant__isnull=True).update(tenant=tenant)
        Service.objects.filter(tenant__isnull=True).update(tenant=tenant)
        GeneralSettings.objects.filter(tenant__isnull=True).update(tenant=tenant)

        ProductCategory.objects.filter(tenant__isnull=True).update(tenant=tenant)
        Product.objects.filter(tenant__isnull=True).update(tenant=tenant)

        InventoryItem.objects.filter(tenant__isnull=True).update(tenant=tenant)
        StockMovement.objects.filter(tenant__isnull=True).update(tenant=tenant)

        CustomerProfile.objects.filter(tenant__isnull=True).update(tenant=tenant)
        VehicleEntry.objects.filter(tenant__isnull=True).update(tenant=tenant)
        VehicleJob.objects.filter(tenant__isnull=True).update(tenant=tenant)
        VehicleJobService.objects.filter(tenant__isnull=True).update(tenant=tenant)
        VehicleJobProduct.objects.filter(tenant__isnull=True).update(tenant=tenant)
        VehicleStatusLog.objects.filter(tenant__isnull=True).update(tenant=tenant)

        Wallet.objects.filter(tenant__isnull=True).update(tenant=tenant)
        Payment.objects.filter(tenant__isnull=True).update(tenant=tenant)
        CashflowTransaction.objects.filter(tenant__isnull=True).update(tenant=tenant)

        ReportSnapshot.objects.filter(tenant__isnull=True).update(tenant=tenant)
        NotificationLog.objects.filter(tenant__isnull=True).update(tenant=tenant)

        self.stdout.write(self.style.SUCCESS('Tenant backfill completed.'))
