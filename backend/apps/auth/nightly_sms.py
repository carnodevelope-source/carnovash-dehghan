from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone

from apps.auth.models import CarWash, User
from apps.auth.sms import send_logged_sms
from apps.notifications.services import normalize_phone
from apps.payments.models import CashflowTransaction, Payment
from apps.vehicles.models import VehicleEntry


def _money(value):
    return Decimal(str(value or 0))


def _resolve_target_day(now, force=False):
    local_now = timezone.localtime(now or timezone.now())
    if force:
        return local_now.date() - timedelta(days=1)
    if local_now.hour >= 23:
        return local_now.date()
    if local_now.hour < 6:
        return local_now.date() - timedelta(days=1)
    return None


def _build_summary_text(*, tenant, day, paid_total, vehicle_in_count, vehicle_out_count, wallet_in_total, wallet_out_total):
    return (
        f'خلاصه روز {day.isoformat()} - {tenant.name}\n'
        f'درآمد: {paid_total:,.0f} تومان\n'
        f'ورود: {vehicle_in_count} | خروج: {vehicle_out_count}\n'
        f'واریز: {wallet_in_total:,.0f} | برداشت: {wallet_out_total:,.0f}'
    )


def dispatch_due_nightly_manager_summaries(*, now=None, target_day=None, force=False):
    current = timezone.localtime(now or timezone.now())
    day = target_day or _resolve_target_day(current, force=force)
    if not day:
        return 0

    start = timezone.make_aware(datetime.combine(day, time.min))
    end = timezone.make_aware(datetime.combine(day, time.max))
    sent_count = 0

    for tenant in CarWash.objects.filter(is_active=True).order_by('id'):
        manager = (
            User.objects.filter(tenant=tenant, role='manager', is_active=True)
            .order_by('id')
            .first()
        )
        phone = normalize_phone(getattr(manager, 'phone', '') or '')
        if not manager or not phone:
            continue

        template_code = f'nightly_manager_summary:{day.isoformat()}'
        already_sent = tenant.notification_logs.filter(
            channel='sms',
            status='sent',
            template_code=template_code,
            recipient=phone,
        ).exists()
        if already_sent:
            continue

        paid_total = _money(
            Payment.objects.filter(
                tenant=tenant,
                status=Payment.Status.SUCCESS,
            ).filter(
                Q(paid_at__gte=start, paid_at__lte=end) | Q(paid_at__isnull=True, created_at__gte=start, created_at__lte=end)
            ).aggregate(total=Sum('amount'))['total']
        )
        vehicle_in_count = VehicleEntry.objects.filter(tenant=tenant, check_in_at__gte=start, check_in_at__lte=end).count()
        vehicle_out_count = VehicleEntry.objects.filter(
            tenant=tenant,
            status=VehicleEntry.Status.RELEASED,
            released_at__gte=start,
            released_at__lte=end,
        ).count()
        wallet_in_total = _money(
            CashflowTransaction.objects.filter(
                tenant=tenant,
                direction=CashflowTransaction.Direction.IN,
                transacted_at__gte=start,
                transacted_at__lte=end,
            ).aggregate(total=Sum('amount'))['total']
        )
        wallet_out_total = _money(
            CashflowTransaction.objects.filter(
                tenant=tenant,
                direction=CashflowTransaction.Direction.OUT,
                transacted_at__gte=start,
                transacted_at__lte=end,
            ).aggregate(total=Sum('amount'))['total']
        )

        text = _build_summary_text(
            tenant=tenant,
            day=day,
            paid_total=paid_total,
            vehicle_in_count=vehicle_in_count,
            vehicle_out_count=vehicle_out_count,
            wallet_in_total=wallet_in_total,
            wallet_out_total=wallet_out_total,
        )
        result = send_logged_sms(
            tenant=tenant,
            text=text,
            phone=phone,
            template_code=template_code,
            payload={'report_date': day.isoformat(), 'tenant_name': tenant.name},
            created_by=manager,
            description='ارسال پیامک خلاصه شبانه مدیر',
            reference_type='nightly_manager_summary',
            charge_tenant_wallet=False,
        )
        if result.get('ok'):
            sent_count += 1
    return sent_count
