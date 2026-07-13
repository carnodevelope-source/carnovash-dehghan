from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.auth.models import CarWash, CarWashFeaturePurchase, User
from apps.notifications.models import NotificationLog
from apps.notifications.services import format_toman, normalize_phone, send_provider_sms
from apps.payments.views import FEATURE_OPTION_CATALOG, WalletBaseMixin


def send_due_installment_sms(tenant, purchase):
    manager = User.objects.filter(tenant=tenant, role='manager', is_active=True, is_deleted=False).order_by('id').first()
    phone = normalize_phone(getattr(manager, 'phone', '') or '')
    if not phone:
        return False
    today = timezone.localdate()
    already_sent = NotificationLog.objects.filter(
        tenant=tenant,
        channel=NotificationLog.Channel.SMS,
        template_code='feature_installment_due',
        recipient=phone,
        created_at__date=today,
        payload__purchase_id=purchase.id,
    ).exists()
    if already_sent:
        return False
    feature_title = FEATURE_OPTION_CATALOG.get(purchase.feature_key, {}).get('title', 'آپشن نرم‌افزار')
    text = (
        f'یادآوری سررسید کارنوواش\n'
        f'کارواش: {tenant.name}\n'
        f'مورد: {feature_title}\n'
        f'مبلغ سررسید: {format_toman(purchase.monthly_installment_amount)}\n'
        f'لطفاً کیف پول اصلی را شارژ یا قسط را پرداخت کنید. بعد از ۷ روز عدم پرداخت، دسترسی قفل می‌شود.'
    )
    result = send_provider_sms(tenant, text, [phone])
    NotificationLog.objects.create(
        tenant=tenant,
        channel=NotificationLog.Channel.SMS,
        recipient=phone,
        template_code='feature_installment_due',
        payload={'purchase_id': purchase.id, 'feature_key': purchase.feature_key},
        status=NotificationLog.Status.SENT if result.get('ok') else NotificationLog.Status.FAILED,
        sent_at=timezone.now() if result.get('ok') else None,
        provider_response=str(result.get('message') or ''),
    )
    return bool(result.get('ok'))


class Command(WalletBaseMixin, BaseCommand):
    help = 'Collects due installment payments for active feature purchases from each tenant wallet.'

    def handle(self, *args, **options):
        processed_tenants = 0
        charged_tenants = 0
        reminded_installments = 0

        for tenant in CarWash.objects.filter(is_active=True).order_by('id'):
            processed_tenants += 1
            with transaction.atomic():
                wallet_before = self._get_or_create_default_wallet(tenant)
                before_balance = wallet_before.balance
                wallet_after = self._collect_due_installments(tenant)
                after_balance = wallet_after.balance if wallet_after is not None else before_balance
            if after_balance != before_balance:
                charged_tenants += 1
            due_purchases = CarWashFeaturePurchase.objects.filter(
                tenant=tenant,
                is_active=True,
                payment_plan=CarWashFeaturePurchase.PaymentPlan.INSTALLMENT,
                remaining_amount__gt=0,
                next_installment_due_at__isnull=False,
                next_installment_due_at__lte=timezone.now(),
            )
            for purchase in due_purchases:
                if send_due_installment_sms(tenant, purchase):
                    reminded_installments += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Processed {processed_tenants} tenants. Charged installments for {charged_tenants} tenants. Sent {reminded_installments} reminders.'
            )
        )
