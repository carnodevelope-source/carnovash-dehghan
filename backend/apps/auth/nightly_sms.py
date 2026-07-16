from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone

from apps.auth.models import CarWash, User
from apps.auth.sms import send_logged_sms
from apps.notifications.models import NotificationLog
from apps.notifications.services import format_jalali_date, format_toman, normalize_phone, to_persian_digits
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


def _day_bounds(day):
    start = timezone.make_aware(datetime.combine(day, time.min))
    return start, start + timedelta(days=1)


def _build_summary_text(*, tenant, day, paid_total, vehicle_in_count, vehicle_out_count, wallet_in_total, wallet_out_total):
    day_label = format_jalali_date(timezone.make_aware(datetime.combine(day, time.min)))
    return (
        f'خلاصه روز {day_label} - {tenant.name}\n'
        f'درآمد: {format_toman(paid_total)}\n'
        f'ورود: {to_persian_digits(vehicle_in_count)} | خروج: {to_persian_digits(vehicle_out_count)}\n'
        f'واریز: {format_toman(wallet_in_total)} | برداشت: {format_toman(wallet_out_total)}'
    )


def _nightly_template_code(tenant, day):
    return f'nightly_manager_summary:{tenant.id}:{day.isoformat()}'


def _has_sent_or_pending_summary(tenant, day, template_code):
    return tenant.notification_logs.filter(
        channel=NotificationLog.Channel.SMS,
        status__in=[NotificationLog.Status.PENDING, NotificationLog.Status.SENT],
        template_code__in=[template_code, f'nightly_manager_summary:{day.isoformat()}'],
    ).exists()


def _summary_payload(*, tenant, day, paid_total, vehicle_in_count, vehicle_out_count, wallet_in_total, wallet_out_total):
    return {
        'report_date': day.isoformat(),
        'tenant_id': tenant.id,
        'tenant_name': tenant.name,
        'paid_total': float(paid_total),
        'vehicle_in_count': vehicle_in_count,
        'vehicle_out_count': vehicle_out_count,
        'wallet_in_total': float(wallet_in_total),
        'wallet_out_total': float(wallet_out_total),
    }


def dispatch_due_nightly_manager_summaries(*, now=None, target_day=None, force=False):
    current = timezone.localtime(now or timezone.now())
    day = target_day or _resolve_target_day(current, force=force)
    if not day:
        return 0

    start, end = _day_bounds(day)
    sent_count = 0

    for tenant in CarWash.objects.filter(is_active=True).order_by('id'):
        template_code = _nightly_template_code(tenant, day)
        if _has_sent_or_pending_summary(tenant, day, template_code):
            continue

        manager = (
            User.objects.filter(tenant=tenant, role='manager', is_active=True)
            .order_by('id')
            .first()
        )
        phone = normalize_phone(getattr(manager, 'phone', '') or '')
        if not manager or not phone:
            continue

        paid_total = _money(
            Payment.objects.filter(
                tenant=tenant,
                status=Payment.Status.SUCCESS,
            ).filter(
                Q(paid_at__gte=start, paid_at__lt=end)
                | Q(paid_at__isnull=True, created_at__gte=start, created_at__lt=end)
            ).aggregate(total=Sum('amount'))['total']
        )
        vehicle_in_count = VehicleEntry.objects.filter(
            tenant=tenant,
            check_in_at__gte=start,
            check_in_at__lt=end,
        ).count()
        vehicle_out_count = VehicleEntry.objects.filter(
            tenant=tenant,
            status=VehicleEntry.Status.RELEASED,
            released_at__gte=start,
            released_at__lt=end,
        ).count()
        wallet_in_total = _money(
            CashflowTransaction.objects.filter(
                tenant=tenant,
                direction=CashflowTransaction.Direction.IN,
                transacted_at__gte=start,
                transacted_at__lt=end,
            ).aggregate(total=Sum('amount'))['total']
        )
        wallet_out_total = _money(
            CashflowTransaction.objects.filter(
                tenant=tenant,
                direction=CashflowTransaction.Direction.OUT,
                transacted_at__gte=start,
                transacted_at__lt=end,
            ).aggregate(total=Sum('amount'))['total']
        )

        payload = _summary_payload(
            tenant=tenant,
            day=day,
            paid_total=paid_total,
            vehicle_in_count=vehicle_in_count,
            vehicle_out_count=vehicle_out_count,
            wallet_in_total=wallet_in_total,
            wallet_out_total=wallet_out_total,
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
            payload=payload,
            created_by=manager,
            description='ارسال پیامک خلاصه شبانه مدیر',
            reference_type='nightly_manager_summary',
            charge_tenant_wallet=False,
        )
        if result.get('ok'):
            sent_count += 1
    return sent_count
