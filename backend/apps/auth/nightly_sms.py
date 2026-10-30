from datetime import datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.db.models import OuterRef, Q, Subquery, Sum
from django.utils import timezone

from apps.auth.models import CarWash, User
from apps.auth.sms import send_logged_sms
from apps.notifications.models import NotificationLog
from apps.notifications.services import format_jalali_date, format_toman, normalize_phone, to_persian_digits
from apps.payments.models import Payment
from apps.vehicles.models import VehicleEntry, VehicleStatusLog


REPORT_TZ = ZoneInfo('Asia/Tehran')


def _money(value):
    return Decimal(str(value or 0))


def _resolve_target_day(now, force=False):
    local_now = timezone.localtime(now or timezone.now(), REPORT_TZ)
    if force:
        return local_now.date()
    if local_now.hour == 23 and local_now.minute >= 59:
        return local_now.date()
    if local_now.hour < 6:
        return local_now.date() - timedelta(days=1)
    return None


def _day_bounds(day):
    start = timezone.make_aware(datetime.combine(day, time.min), REPORT_TZ)
    return start, start + timedelta(days=1)


def _build_summary_text(*, tenant, day, paid_total, vehicle_in_count, vehicle_out_count, vehicle_pending_count, vehicle_cancelled_count, vehicle_remaining_count, history_unknown_count):
    with timezone.override(REPORT_TZ):
        day_label = format_jalali_date(_day_bounds(day)[0])

    return (
        f'گزارش شبانه {tenant.name}\n'
        f'تاریخ: {day_label}\n'
        f'درآمد وصول‌شده: {format_toman(paid_total)}\n'
        f'خودروهای پذیرش‌شده: {to_persian_digits(str(vehicle_in_count))}\n'
        f'خودروهای ترخیص‌شده: {to_persian_digits(str(vehicle_out_count))}\n'
        f'آماده ترخیص: {to_persian_digits(str(vehicle_pending_count))}\n'
        f'لغو شده‌ها: {to_persian_digits(str(vehicle_cancelled_count))}'
    )


def _nightly_template_code(tenant, day):
    return f'nightly_manager_summary:{tenant.id}:{day.isoformat()}'


def _has_sent_or_pending_summary(tenant, day, template_code):
    return tenant.notification_logs.filter(
        channel=NotificationLog.Channel.SMS,
        status__in=[NotificationLog.Status.PENDING, NotificationLog.Status.SENT],
        template_code__in=[template_code, f'nightly_manager_summary:{day.isoformat()}'],
    ).exists()


def _summary_payload(*, tenant, day, paid_total, vehicle_in_count, vehicle_out_count, vehicle_pending_count, vehicle_cancelled_count, vehicle_remaining_count, history_unknown_count):
    return {
        'report_date': day.isoformat(),
        'tenant_id': tenant.id,
        'tenant_name': tenant.name,
        'paid_total': float(paid_total),
        'vehicle_in_count': vehicle_in_count,
        'vehicle_out_count': vehicle_out_count,
        'vehicle_pending_count': vehicle_pending_count,
        'vehicle_cancelled_count': vehicle_cancelled_count,
        'vehicle_remaining_count': vehicle_remaining_count,
        'history_unknown_count': history_unknown_count,
    }


def _historical_inventory(tenant, end):
    """Use the last transition before midnight, or the next transition's source.

    Total remaining inventory requires historical evidence. Daily ready counts
    fall back to recorded status for legacy entries without history. released_at
    is independent evidence of release unless a later transition exists.
    """
    logs = VehicleStatusLog.objects.filter(tenant=tenant, vehicle_id=OuterRef('pk'))
    before = logs.filter(changed_at__lt=end).order_by('-changed_at', '-pk')
    after = logs.filter(changed_at__gte=end).order_by('changed_at', 'pk')
    entries = VehicleEntry.objects.filter(tenant=tenant, check_in_at__lt=end).annotate(
        historical_status=Subquery(before.values('to_status')[:1]),
        historical_at=Subquery(before.values('changed_at')[:1]),
        next_source=Subquery(after.values('from_status')[:1]),
    ).values('historical_status', 'historical_at', 'next_source', 'released_at', 'check_in_at', 'status')
    ready = remaining = unknown = 0
    active = {VehicleEntry.Status.ENTERED, VehicleEntry.Status.ASSIGNED,
              VehicleEntry.Status.IN_PROGRESS, VehicleEntry.Status.READY_TO_SETTLE}
    for entry in entries.iterator():
        status = entry['historical_status'] or entry['next_source']
        released_at = entry['released_at']
        if released_at and released_at < end and (
            entry['historical_at'] is None or released_at >= entry['historical_at']
        ):
            status = VehicleEntry.Status.RELEASED
        # Ready count covers admissions on the report day only. For legacy
        # entries without transitions, use their recorded current status.
        ready_status = status or entry['status']
        if entry['check_in_at'] >= end - timedelta(days=1):
            ready += ready_status == VehicleEntry.Status.READY_TO_SETTLE
        if status in active:
            remaining += 1
        elif status not in {VehicleEntry.Status.RELEASED, VehicleEntry.Status.CANCELLED}:
            unknown += 1
    # Keep missing historical evidence explicit for total remaining inventory.
    return (ready, None if unknown else remaining, unknown)


def dispatch_due_nightly_manager_summaries(*, now=None, target_day=None, force=False):
    current = timezone.localtime(now or timezone.now(), REPORT_TZ)
    day = target_day or _resolve_target_day(current, force=force)
    if not day:
        return 0

    start, end = _day_bounds(day)
    if current < end:
        return 0  # A complete end-of-day snapshot is not available yet.
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
        daily_logs = VehicleStatusLog.objects.filter(
            tenant=tenant, vehicle__tenant=tenant,
            changed_at__gte=start, changed_at__lt=end,
        )
        vehicle_out_count = VehicleEntry.objects.filter(tenant=tenant).filter(
            Q(released_at__gte=start, released_at__lt=end)
            | Q(pk__in=daily_logs.filter(to_status=VehicleEntry.Status.RELEASED).values('vehicle_id'))
        ).count()
        vehicle_pending_count, vehicle_remaining_count, history_unknown_count = _historical_inventory(tenant, end)
        vehicle_cancelled_count = daily_logs.filter(
            to_status=VehicleEntry.Status.CANCELLED,
        ).values('vehicle_id').distinct().count()

        payload = _summary_payload(
            tenant=tenant,
            day=day,
            paid_total=paid_total,
            vehicle_in_count=vehicle_in_count,
            vehicle_out_count=vehicle_out_count,
            vehicle_pending_count=vehicle_pending_count,
            vehicle_cancelled_count=vehicle_cancelled_count,
            vehicle_remaining_count=vehicle_remaining_count,
            history_unknown_count=history_unknown_count,
        )
        text = _build_summary_text(
            tenant=tenant,
            day=day,
            paid_total=paid_total,
            vehicle_in_count=vehicle_in_count,
            vehicle_out_count=vehicle_out_count,
            vehicle_pending_count=vehicle_pending_count,
            vehicle_cancelled_count=vehicle_cancelled_count,
            vehicle_remaining_count=vehicle_remaining_count,
            history_unknown_count=history_unknown_count,
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
