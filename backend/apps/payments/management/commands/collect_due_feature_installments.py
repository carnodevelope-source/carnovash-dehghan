from django.core.management.base import BaseCommand
from django.db import transaction

from apps.auth.models import CarWash
from apps.payments.views import WalletBaseMixin


class Command(WalletBaseMixin, BaseCommand):
    help = 'Collects due installment payments for active feature purchases from each tenant wallet.'

    def handle(self, *args, **options):
        processed_tenants = 0
        charged_tenants = 0

        for tenant in CarWash.objects.filter(is_active=True).order_by('id'):
            processed_tenants += 1
            with transaction.atomic():
                wallet_before = self._get_or_create_default_wallet(tenant)
                before_balance = wallet_before.balance
                wallet_after = self._collect_due_installments(tenant)
                after_balance = wallet_after.balance if wallet_after is not None else before_balance
            if after_balance != before_balance:
                charged_tenants += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Processed {processed_tenants} tenants. Charged installments for {charged_tenants} tenants.'
            )
        )
