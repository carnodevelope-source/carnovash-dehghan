from datetime import datetime, time
from decimal import Decimal, ROUND_HALF_UP

from django.http import HttpResponse
from django.db import transaction
from django.db.models import Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payments.models import Payment
from apps.vehicles.models import BlockedPlate, VehicleEntry, VehicleJob
from apps.workers.models import WorkerAttendance, WorkerProfile
from apps.reports.models import WorkerPayoutTransaction


import csv


def _parse_dt(value, end_of_day=False):
    if not value:
        return None
    dt = datetime.strptime(value, '%Y-%m-%d')
    dt = datetime.combine(dt.date(), time.max if end_of_day else time.min)
    return timezone.make_aware(dt)


def _normalize_decimal(value):
    return Decimal(str(value or 0))


def _decimal_hours_from_minutes(minutes):
    return (Decimal(str(minutes or 0)) / Decimal('60')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _normalize_jalali_month(value):
    normalized = str(value or '').strip().replace('-', '/')
    parts = normalized.split('/')
    if len(parts) == 3:
        parts = parts[:2]
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        return ''
    year = int(parts[0])
    month = int(parts[1])
    if year < 1300 or year > 1600 or month < 1 or month > 12:
        return ''
    return f'{year:04d}/{month:02d}'


def _gregorian_to_jalali(date_obj):
    gy = int(date_obj.year) - 1600
    gm = int(date_obj.month) - 1
    gd = int(date_obj.day) - 1
    g_days_in_month = [
        31,
        29 if ((date_obj.year % 4 == 0 and date_obj.year % 100 != 0) or (date_obj.year % 400 == 0)) else 28,
        31, 30, 31, 30, 31, 31, 30, 31, 30, 31,
    ]
    j_days_in_month = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]
    g_day_no = 365 * gy + (gy + 3) // 4 - (gy + 99) // 100 + (gy + 399) // 400
    for idx in range(gm):
        g_day_no += g_days_in_month[idx]
    g_day_no += gd
    j_day_no = g_day_no - 79
    j_np = j_day_no // 12053
    j_day_no %= 12053
    jy = 979 + 33 * j_np + 4 * (j_day_no // 1461)
    j_day_no %= 1461
    if j_day_no >= 366:
        jy += (j_day_no - 1) // 365
        j_day_no = (j_day_no - 1) % 365
    jm = 0
    while jm < 11 and j_day_no >= j_days_in_month[jm]:
        j_day_no -= j_days_in_month[jm]
        jm += 1
    return jy, jm + 1, j_day_no + 1


def _jalali_month_from_gregorian(value):
    if not value:
        return ''
    jy, jm, _jd = _gregorian_to_jalali(value)
    return f'{jy:04d}/{jm:02d}'


def _current_jalali_month():
    return _jalali_month_from_gregorian(timezone.localdate())


def _jalali_month_tuple(value):
    normalized = _normalize_jalali_month(value)
    if not normalized:
        return None
    year, month = normalized.split('/')
    return int(year), int(month)


def _jalali_months_between(start_month, end_month):
    start_tuple = _jalali_month_tuple(start_month)
    end_tuple = _jalali_month_tuple(end_month)
    if not start_tuple or not end_tuple:
        return 0
    start_index = start_tuple[0] * 12 + start_tuple[1]
    end_index = end_tuple[0] * 12 + end_tuple[1]
    if end_index < start_index:
        return 0
    return (end_index - start_index) + 1


def _jalali_next_month(value):
    month_tuple = _jalali_month_tuple(value)
    if not month_tuple:
        return ''
    year, month = month_tuple
    if month >= 12:
        return f'{year + 1:04d}/01'
    return f'{year:04d}/{month + 1:02d}'


def _jalali_month_lte(left, right):
    left_tuple = _jalali_month_tuple(left)
    right_tuple = _jalali_month_tuple(right)
    if not left_tuple or not right_tuple:
        return False
    return left_tuple <= right_tuple


def _jalali_month_eq(left, right):
    left_tuple = _jalali_month_tuple(left)
    right_tuple = _jalali_month_tuple(right)
    if not left_tuple or not right_tuple:
        return False
    return left_tuple == right_tuple


def _resolve_worker_insurance_start_month(worker):
    if not worker:
        return ''
    if getattr(worker, 'started_at', None):
        return _jalali_month_from_gregorian(worker.started_at)
    user = getattr(worker, 'user', None)
    if getattr(user, 'date_joined', None):
        joined_at = timezone.localtime(user.date_joined) if timezone.is_aware(user.date_joined) else user.date_joined
        return _jalali_month_from_gregorian(joined_at.date())
    if getattr(worker, 'created_at', None):
        created_at = timezone.localtime(worker.created_at) if timezone.is_aware(worker.created_at) else worker.created_at
        return _jalali_month_from_gregorian(created_at.date())
    return ''


def _insurance_paid_amount_for_month(worker, month_value):
    normalized_month = _normalize_jalali_month(month_value)
    if not worker or not normalized_month:
        return Decimal('0')
    total = WorkerPayoutTransaction.objects.filter(
        worker=worker,
        kind=WorkerPayoutTransaction.Kind.INSURANCE_PAYMENT,
        reference_month=normalized_month,
    ).aggregate(total=Coalesce(Sum('amount'), Value(Decimal('0'))))['total']
    return _normalize_decimal(total)


def _insurance_paid_amount_until_month(worker, target_month):
    normalized_month = _normalize_jalali_month(target_month)
    if not worker or not normalized_month:
        return Decimal('0')
    total = Decimal('0')
    month_values = (
        WorkerPayoutTransaction.objects
        .filter(worker=worker, kind=WorkerPayoutTransaction.Kind.INSURANCE_PAYMENT)
        .exclude(reference_month='')
        .values_list('reference_month', 'amount')
    )
    for reference_month, amount in month_values:
        if _jalali_month_lte(reference_month, normalized_month):
            total += _normalize_decimal(amount)
    return total


def _format_export_datetime(value):
    if not value:
        return ''
    localized = timezone.localtime(value) if timezone.is_aware(value) else value
    return localized.strftime('%Y-%m-%d %H:%M')


def _driver_gender_label(value):
    return {'male': 'آقا', 'female': 'خانم'}.get(str(value or '').strip().lower(), '')


def _export_row_value(row, field):
    value = row.get(field, '')
    if field in {'created_at', 'event_at'}:
        return _format_export_datetime(value)
    if field == 'reminder_due_at':
        return _format_export_datetime(value)[:10] if value else ''
    if field == 'driver_gender':
        return _driver_gender_label(value)
    if value is None:
        return ''
    return value


def _build_export_config(tab_key):
    configs = {
        'overall': {'filename': 'overall-report', 'headers': [('row', 'ردیف'), ('driver_name', 'نام راننده'), ('driver_gender', 'جنسیت'), ('driver_phone', 'شماره'), ('car_model', 'مدل'), ('car_color', 'رنگ'), ('plate_number', 'پلاک'), ('status', 'وضعیت'), ('carwash_share', 'حق کارواش'), ('worker_share', 'حق نیرو'), ('discount_total', 'تخفیف'), ('tax_total', 'مالیات'), ('tip_amount', 'انعام'), ('worker_name', 'نام نیرو'), ('services', 'خدمات'), ('created_at', 'تاریخ')], 'rows_key': 'overall_report'},
        'carwash': {'filename': 'carwash-share-report', 'headers': [('row', 'ردیف'), ('driver_name', 'نام راننده'), ('driver_phone', 'شماره'), ('car_model', 'مدل'), ('car_color', 'رنگ'), ('plate_number', 'پلاک'), ('carwash_share', 'حق کارواش'), ('worker_name', 'نام نیرو'), ('created_at', 'تاریخ')], 'rows_key': 'carwash_report'},
        'worker': {'filename': 'worker-share-report', 'headers': [('row', 'ردیف'), ('driver_name', 'نام راننده'), ('car_model', 'مدل'), ('car_color', 'رنگ'), ('plate_number', 'پلاک'), ('final_total_without_tip', 'مبلغ سفارش بدون انعام'), ('discount_total', 'تخفیف'), ('tip_amount', 'انعام'), ('worker_share', 'حق نیرو'), ('worker_name', 'نام نیرو'), ('created_at', 'تاریخ')], 'rows_key': 'worker_report'},
        'tips': {'filename': 'tips-report', 'headers': [('row', 'ردیف'), ('driver_name', 'نام راننده'), ('driver_phone', 'شماره'), ('car_model', 'مدل'), ('car_color', 'رنگ'), ('plate_number', 'پلاک'), ('tip_amount', 'انعام'), ('worker_name', 'نام نیرو'), ('products', 'کالا'), ('created_at', 'تاریخ')], 'rows_key': 'tips_report'},
        'revenue': {'filename': 'revenue-report', 'headers': [('row', 'ردیف'), ('created_at', 'تاریخ'), ('driver_name', 'نام راننده'), ('driver_phone', 'شماره'), ('car_model', 'مدل خودرو'), ('car_color', 'رنگ'), ('plate_number', 'پلاک'), ('payment_method', 'روش پرداخت'), ('payment_status', 'وضعیت پرداخت'), ('service_amount', 'خدمات'), ('product_amount', 'محصولات'), ('discount_amount', 'تخفیف'), ('tip_amount', 'انعام'), ('tax_amount', 'مالیات'), ('final_total', 'مبلغ نهایی'), ('received_amount', 'وصول شده'), ('outstanding_amount', 'مانده'), ('cheque_number', 'شماره چک'), ('reminder_due_at', 'سررسید')], 'rows_key': 'revenue_report'},
        'attendance': {'filename': 'attendance-report', 'headers': [('row', 'ردیف'), ('worker_name', 'نام پرسنل'), ('event_type', 'نوع رویداد'), ('source', 'منبع ثبت'), ('event_at', 'زمان')], 'rows_key': 'attendance_report'},
        'blacklist': {'filename': 'blacklist-report', 'headers': [('row', 'ردیف'), ('plate_number', 'پلاک'), ('plate_type', 'نوع وسیله'), ('note', 'توضیح'), ('blocked_by_name', 'ثبت کننده'), ('created_at', 'تاریخ ثبت')], 'rows_key': 'blacklist_report'},
        'discount': {
            'filename': 'discount-report',
            'headers': [
                ('row', 'ردیف'),
                ('driver_name', 'نام راننده'),
                ('driver_phone', 'شماره'),
                ('plate_number', 'پلاک'),
                ('facility_discount_total', 'تخفیف مجموعه'),
                ('loyalty_discount_total', 'تخفیف امتیاز مشتری'),
                ('manual_discount_total', 'تخفیف دستی'),
                ('discount_total', 'جمع تخفیف'),
                ('created_at', 'تاریخ'),
            ],
            'rows_key': 'discount_report',
        },
    }
    return configs.get(tab_key, configs['overall'])


def _job_discount_total(job):
    if not job:
        return Decimal('0')
    total = _normalize_decimal(getattr(job, 'total_discount', 0) or getattr(job, 'discount_total', 0))
    if total > 0:
        return total
    return (
        _normalize_decimal(getattr(job, 'facility_discount_total', 0))
        + _normalize_decimal(getattr(job, 'loyalty_discount_total', 0))
        + _normalize_decimal(getattr(job, 'manual_discount_total', 0))
    )


def _worker_name(worker):
    if not worker or not getattr(worker, 'user', None):
        return '-'
    return worker.user.full_name or worker.user.username or '-'


def _job_worker_names(job):
    if not job:
        return '-'
    snapshot = job.assigned_workers_snapshot if isinstance(job.assigned_workers_snapshot, list) else []
    names = []
    for item in snapshot:
        if not isinstance(item, dict):
            continue
        name = str(item.get('name') or '').strip()
        if name and name not in names:
            names.append(name)
    if names:
        return '، '.join(names)
    return _worker_name(job.assigned_worker)


def _job_has_worker(job, worker_id):
    if not worker_id or not job:
        return True
    if job.assigned_worker_id == worker_id:
        return True
    snapshot = job.assigned_workers_snapshot if isinstance(job.assigned_workers_snapshot, list) else []
    for item in snapshot:
        try:
            if int(item.get('id')) == int(worker_id):
                return True
        except (TypeError, ValueError, AttributeError):
            continue
    return False


def _job_worker_ids(job):
    if not job:
        return []
    result = []
    snapshot = job.assigned_workers_snapshot if isinstance(job.assigned_workers_snapshot, list) else []
    for item in snapshot:
        try:
            worker_id = int(item.get('id'))
        except (TypeError, ValueError, AttributeError):
            continue
        if worker_id > 0 and worker_id not in result:
            result.append(worker_id)
    if job.assigned_worker_id and int(job.assigned_worker_id) not in result:
        result.insert(0, int(job.assigned_worker_id))
    return result


def _job_worker_distribution_percent_for(job, worker_id):
    snapshot = job.assigned_workers_snapshot if isinstance(job.assigned_workers_snapshot, list) else []
    for item in snapshot:
        try:
            if int(item.get('id')) != int(worker_id):
                continue
        except (TypeError, ValueError, AttributeError):
            continue
        if item.get('worker_share_percent') is not None:
            percent = _normalize_decimal(item.get('worker_share_percent'))
            return min(Decimal('100'), max(Decimal('0'), percent))
    worker_ids = _job_worker_ids(job)
    if not worker_ids or int(worker_id) not in worker_ids:
        return Decimal('0')
    return Decimal('100') / Decimal(str(len(worker_ids)))


def _job_final_total_without_tip(job):
    """Final charged order amount excluding tip (sale after discounts)."""
    if not job:
        return Decimal('0')
    return max(
        Decimal('0'),
        _normalize_decimal(getattr(job, 'final_total', 0)) - _normalize_decimal(getattr(job, 'tip_amount', 0)),
    )


def _job_share_base_total(job):
    """Commission base used at checkout: services only after line discounts (never products or rate-card list prices)."""
    if not job:
        return Decimal('0')
    services_total = _normalize_decimal(getattr(job, 'services_total', 0))
    if services_total <= 0:
        services_total = sum(
            (
                _normalize_decimal(getattr(line, 'line_total', 0))
                for line in job.service_lines.all()
            ),
            Decimal('0'),
        )
    return max(Decimal('0'), services_total)


def _job_worker_service_total_for(job, worker_id):
    """Worker-attributed share base (not list/rate-card prices)."""
    share_base = _job_share_base_total(job)
    if not worker_id:
        return share_base
    percent = _job_worker_distribution_percent_for(job, worker_id)
    return (share_base * percent) / Decimal('100')


def _job_worker_commission_percent_for(job):
    if getattr(job, 'worker_payment_type', '') != VehicleJob.WorkerPaymentType.PERCENT:
        return Decimal('0')
    return min(Decimal('100'), max(Decimal('0'), _normalize_decimal(job.worker_payment_percent)))


def _job_worker_share_for(job, worker_id):
    """Per-worker share owed for a job. Prefer checkout snapshot; never inflate with rate-card prices."""
    if not job or not worker_id:
        return Decimal('0')
    worker_ids = _job_worker_ids(job)
    if not worker_ids or int(worker_id) not in {int(item) for item in worker_ids}:
        return Decimal('0')

    snapshot = job.assigned_workers_snapshot if isinstance(job.assigned_workers_snapshot, list) else []
    for item in snapshot:
        try:
            if int(item.get('id')) != int(worker_id):
                continue
        except (TypeError, ValueError, AttributeError):
            continue
        # Explicit zero in snapshot is often leftover from assignment/release sync bugs.
        # Only trust positive snapshot amounts; otherwise fall back to job totals.
        if item.get('worker_share_amount') is not None:
            snapshot_amount = max(Decimal('0'), _normalize_decimal(item.get('worker_share_amount')))
            if snapshot_amount > 0:
                return snapshot_amount
        break

    total = _normalize_decimal(getattr(job, 'worker_share_amount', 0))
    if total > 0:
        distribution_percent = _job_worker_distribution_percent_for(job, worker_id)
        if distribution_percent > 0:
            return (total * distribution_percent) / Decimal('100')
        if len(worker_ids) == 1:
            return total

    commission_percent = _job_worker_commission_percent_for(job)
    if commission_percent > 0:
        worker_base = _job_worker_service_total_for(job, worker_id)
        return (worker_base * commission_percent) / Decimal('100')

    return Decimal('0')


def _money_q(value):
    return _normalize_decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _query_flag(value):
    return str(value or '').strip().lower() in {'1', 'true', 'yes', 'on'}


def _parse_sync_limit(value, default=None):
    if value is None or str(value).strip() == '':
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    if parsed < 0:
        return default
    return parsed


def _snapshot_items(job):
    snapshot = getattr(job, 'assigned_workers_snapshot', None)
    if not isinstance(snapshot, list):
        return []
    return [dict(item) for item in snapshot if isinstance(item, dict)]


def _recover_job_commission_percent(job):
    """Return (percent, should_persist) for percent-paid jobs with a missing commission rate."""
    stored = min(Decimal('100'), max(Decimal('0'), _normalize_decimal(getattr(job, 'worker_payment_percent', 0))))
    if stored > 0:
        return stored, False
    worker = getattr(job, 'assigned_worker', None)
    if not worker:
        return Decimal('0'), False
    payment_type = str(getattr(worker, 'payment_type', '') or '').strip().lower()
    if payment_type and payment_type != WorkerProfile.PaymentType.PERCENT:
        return Decimal('0'), False
    recovered = min(Decimal('100'), max(Decimal('0'), _normalize_decimal(getattr(worker, 'default_commission_percent', 0))))
    if recovered <= 0:
        return Decimal('0'), False
    return recovered, True


def _expected_worker_share_total(job, share_base):
    share_base = max(Decimal('0'), _money_q(share_base))
    payment_type = getattr(job, 'worker_payment_type', '') or VehicleJob.WorkerPaymentType.PERCENT
    stored_share = min(share_base, _money_q(getattr(job, 'worker_share_amount', 0)))
    if payment_type == VehicleJob.WorkerPaymentType.HOURLY:
        return stored_share, False, _normalize_decimal(getattr(job, 'worker_payment_percent', 0))
    if payment_type == VehicleJob.WorkerPaymentType.FIXED:
        expected = min(share_base, _money_q(getattr(job, 'worker_payment_fixed', 0)))
        if expected <= 0:
            worker = getattr(job, 'assigned_worker', None)
            expected = min(share_base, _money_q(getattr(worker, 'default_fixed_wage', 0))) if worker else Decimal('0')
        if expected <= 0:
            expected = stored_share
        return expected, False, _normalize_decimal(getattr(job, 'worker_payment_percent', 0))

    percent, persist_percent = _recover_job_commission_percent(job)
    if percent <= 0 and share_base > 0 and stored_share > 0:
        percent = min(Decimal('100'), _money_q((stored_share * Decimal('100')) / share_base))
        persist_percent = percent > 0
    if percent > 0:
        return _money_q((share_base * percent) / Decimal('100')), persist_percent, percent
    return stored_share, persist_percent, percent


def _distribute_by_percent(total, percents):
    total = _money_q(total)
    count = len(percents)
    if count <= 0:
        return []
    if total <= 0:
        return [Decimal('0')] * count
    amounts = []
    distributed = Decimal('0')
    for index, percent in enumerate(percents):
        if index == count - 1:
            amount = max(Decimal('0'), total - distributed)
        else:
            amount = _money_q((total * max(Decimal('0'), _normalize_decimal(percent))) / Decimal('100'))
        amounts.append(amount)
        distributed += amount
    return amounts


def _build_synced_snapshot(job, worker_share_total, tip_amount):
    worker_ids = _job_worker_ids(job)
    snapshot = _snapshot_items(job)
    by_id = {}
    for item in snapshot:
        try:
            worker_id = int(item.get('id'))
        except (TypeError, ValueError, AttributeError):
            continue
        if worker_id > 0:
            by_id[worker_id] = item
    ordered_ids = []
    for worker_id in worker_ids:
        if worker_id not in ordered_ids:
            ordered_ids.append(int(worker_id))
    if not ordered_ids and job.assigned_worker_id:
        ordered_ids = [int(job.assigned_worker_id)]
    if not ordered_ids:
        return snapshot, False

    percents = []
    for worker_id in ordered_ids:
        item = by_id.get(worker_id) or {}
        if item.get('worker_share_percent') is not None:
            percents.append(_job_worker_distribution_percent_for(job, worker_id))
        else:
            percents.append(Decimal('0'))
    percent_total = sum(percents, Decimal('0'))
    if percent_total <= 0:
        equal = _money_q(Decimal('100') / Decimal(str(len(ordered_ids))))
        percents = [equal] * len(ordered_ids)
        remainder = Decimal('100') - (equal * (len(ordered_ids) - 1))
        percents[-1] = remainder
        percent_total = Decimal('100')
    elif abs(percent_total - Decimal('100')) > Decimal('0.05'):
        scaled = []
        scaled_sum = Decimal('0')
        for index, percent in enumerate(percents):
            if index == len(percents) - 1:
                scaled.append(max(Decimal('0'), Decimal('100') - scaled_sum))
            else:
                value = _money_q((percent * Decimal('100')) / percent_total)
                scaled.append(value)
                scaled_sum += value
        percents = scaled

    tip_percents = []
    for worker_id in ordered_ids:
        item = by_id.get(worker_id) or {}
        if item.get('tip_share_percent') is not None:
            tip_percents.append(min(Decimal('100'), max(Decimal('0'), _normalize_decimal(item.get('tip_share_percent')))))
        else:
            tip_percents.append(Decimal('0'))
    if sum(tip_percents, Decimal('0')) <= 0 and _money_q(tip_amount) > 0:
        tip_percents = list(percents)

    share_amounts = _distribute_by_percent(worker_share_total, percents)
    tip_amounts = _distribute_by_percent(tip_amount, tip_percents)
    assigned_name = _worker_name(getattr(job, 'assigned_worker', None))
    synced = []
    changed = len(snapshot) != len(ordered_ids)
    for index, worker_id in enumerate(ordered_ids):
        item = by_id.get(worker_id) or {}
        name = str(item.get('name') or '').strip()
        if not name or name == '-':
            if job.assigned_worker_id and int(job.assigned_worker_id) == worker_id:
                name = assigned_name if assigned_name != '-' else name
        next_item = {
            **item,
            'id': worker_id,
            'name': name or item.get('name') or '',
            'worker_share_percent': float(_money_q(percents[index])),
            'worker_share_amount': float(share_amounts[index]),
            'tip_share_percent': float(_money_q(tip_percents[index])),
            'tip_share_amount': float(tip_amounts[index]),
        }
        if (
            _money_q(item.get('worker_share_amount')) != share_amounts[index]
            or _money_q(item.get('tip_share_amount')) != tip_amounts[index]
            or _money_q(item.get('worker_share_percent')) != _money_q(percents[index])
            or int(item.get('id') or 0) != worker_id
        ):
            changed = True
        synced.append(next_item)
    return synced, changed


def _expected_carwash_share(job, share_base, worker_share_total, tip_amount, workers_tip_share_amount):
    post_sale_discount = min(
        _money_q(getattr(job, 'services_total', 0)),
        _money_q(getattr(job, 'loyalty_discount_total', 0)) + _money_q(getattr(job, 'manual_discount_total', 0)),
    )
    return max(
        Decimal('0'),
        _money_q(share_base)
        - _money_q(worker_share_total)
        + max(Decimal('0'), _money_q(tip_amount) - _money_q(workers_tip_share_amount))
        - post_sale_discount,
    )


def _expected_final_total(job, share_base, tip_amount):
    stored = _money_q(getattr(job, 'final_total', 0))
    if stored > 0:
        return stored
    service_list = _money_q(getattr(job, 'service_list_subtotal', 0))
    if service_list <= 0:
        service_list = _money_q(getattr(job, 'services_total', 0))
    products_total = _money_q(getattr(job, 'products_total', 0))
    discount_total = _job_discount_total(job)
    tax_total = _money_q(getattr(job, 'tax_total', 0))
    computed = max(Decimal('0'), service_list - discount_total) + products_total + tax_total + _money_q(tip_amount)
    if computed <= 0:
        computed = max(Decimal('0'), _money_q(share_base) - discount_total) + tax_total + _money_q(tip_amount)
    return _money_q(computed)


def _sync_released_job_financials(job):
    """Persist missing worker share / snapshot / tip split so reports stop showing 0."""
    if not job:
        return False
    share_base = _job_share_base_total(job)
    tip_amount = _money_q(getattr(job, 'tip_amount', 0))
    expected_share, persist_percent, percent = _expected_worker_share_total(job, share_base)
    snapshot, snapshot_changed = _build_synced_snapshot(job, expected_share, tip_amount)
    workers_tip = sum((_money_q(item.get('tip_share_amount')) for item in snapshot), Decimal('0'))
    expected_carwash = _expected_carwash_share(job, share_base, expected_share, tip_amount, workers_tip)
    expected_final = _expected_final_total(job, share_base, tip_amount)

    update_fields = []
    if persist_percent and _money_q(getattr(job, 'worker_payment_percent', 0)) != _money_q(percent):
        job.worker_payment_percent = _money_q(percent)
        update_fields.append('worker_payment_percent')
    if _money_q(getattr(job, 'worker_share_amount', 0)) != expected_share:
        job.worker_share_amount = expected_share
        update_fields.append('worker_share_amount')
    if snapshot_changed:
        job.assigned_workers_snapshot = snapshot
        update_fields.append('assigned_workers_snapshot')
    if _money_q(getattr(job, 'workers_tip_share_amount', 0) or 0) != workers_tip:
        job.workers_tip_share_amount = workers_tip if workers_tip > 0 else None
        update_fields.append('workers_tip_share_amount')
    stored_carwash = _money_q(getattr(job, 'carwash_share_amount', 0))
    if stored_carwash != expected_carwash and (
        'worker_share_amount' in update_fields or (stored_carwash <= 0 and expected_carwash > 0)
    ):
        job.carwash_share_amount = expected_carwash
        update_fields.append('carwash_share_amount')
    if _money_q(getattr(job, 'final_total', 0)) <= 0 and expected_final > 0:
        job.final_total = expected_final
        update_fields.append('final_total')
    if not update_fields:
        return False
    if 'updated_at' not in update_fields:
        update_fields.append('updated_at')
    with transaction.atomic():
        job.save(update_fields=update_fields)
    return True


def _sync_released_jobs(jobs, limit=None):
    synced = 0
    checked = 0
    for job in jobs:
        if not job:
            continue
        if limit is not None and checked >= limit:
            break
        checked += 1
        if _sync_released_job_financials(job):
            synced += 1
    return synced


def _job_worker_tip_for(job, worker_id):
    snapshot = job.assigned_workers_snapshot if isinstance(job.assigned_workers_snapshot, list) else []
    for item in snapshot:
        try:
            if int(item.get('id')) == int(worker_id):
                tip_share_amount = item.get('tip_share_amount')
                if tip_share_amount is not None:
                    return _normalize_decimal(tip_share_amount)
        except (TypeError, ValueError, AttributeError):
            continue
    worker_ids = _job_worker_ids(job)
    if not worker_ids or int(worker_id) not in worker_ids:
        return Decimal('0')
    if len(worker_ids) == 1:
        return _normalize_decimal(job.workers_tip_share_amount or job.tip_amount)
    distributed = _normalize_decimal(job.workers_tip_share_amount)
    if distributed <= 0:
        return Decimal('0')
    return distributed / Decimal(str(len(worker_ids)))


def _get_worker_jobs(tenant, worker_id):
    jobs = list(
        VehicleJob.objects.select_related('vehicle')
        .filter(tenant=tenant)
        .exclude(vehicle__status=VehicleEntry.Status.CANCELLED)
    )
    return [job for job in jobs if _job_has_worker(job, worker_id)]


def _compute_worker_attendance_minutes(worker, *, start=None, end=None):
    if not worker:
        return 0

    now = timezone.now()
    effective_end = end or now
    if effective_end > now:
        effective_end = now

    events = WorkerAttendance.objects.filter(worker=worker)
    if end:
        events = events.filter(event_at__lte=end)

    open_started_at = None
    if start:
        # Reading the whole attendance history to answer "hours this month" is
        # what made reports slower every month. One lookup for the shift that
        # may already be open at `start` keeps the result identical.
        previous = (
            WorkerAttendance.objects.filter(worker=worker, event_at__lt=start)
            .order_by('-event_at', '-id')
            .values_list('event_type', flat=True)
            .first()
        )
        if previous == WorkerAttendance.EventType.IN:
            open_started_at = start
        events = events.filter(event_at__gte=start)

    events = list(events.order_by('event_at', 'id').values_list('event_type', 'event_at'))
    if not events and open_started_at is None:
        return 0

    worked_seconds = 0
    for event_type, event_at in events:
        if event_type == WorkerAttendance.EventType.IN:
            open_started_at = event_at
            continue
        if event_type != WorkerAttendance.EventType.OUT or not open_started_at:
            continue
        interval_start = open_started_at
        interval_end = event_at
        open_started_at = None
        if start and interval_end < start:
            continue
        if interval_start > effective_end:
            continue
        clipped_start = max(interval_start, start) if start else interval_start
        clipped_end = min(interval_end, effective_end)
        worked_seconds += max((clipped_end - clipped_start).total_seconds(), 0)

    if open_started_at and open_started_at <= effective_end:
        clipped_start = max(open_started_at, start) if start else open_started_at
        worked_seconds += max((effective_end - clipped_start).total_seconds(), 0)

    return int(worked_seconds // 60)


def _compute_worker_financials(worker, jobs, insurance_month='', start=None, end=None):
    job_ids = [job.id for job in jobs if job]
    transactions = WorkerPayoutTransaction.objects.filter(worker=worker)
    if job_ids:
        transactions = transactions.filter(Q(vehicle_job_id__in=job_ids) | Q(vehicle_job__isnull=True))
    else:
        transactions = transactions.filter(vehicle_job__isnull=True)

    aggregates = transactions.aggregate(
        bonus_total=Coalesce(
            Sum('amount', filter=Q(kind=WorkerPayoutTransaction.Kind.BONUS)),
            Value(Decimal('0')),
        ),
        penalty_total=Coalesce(
            Sum('amount', filter=Q(kind=WorkerPayoutTransaction.Kind.PENALTY)),
            Value(Decimal('0')),
        ),
        wage_paid_total=Coalesce(
            Sum('amount', filter=Q(kind=WorkerPayoutTransaction.Kind.WAGE_PAYMENT)),
            Value(Decimal('0')),
        ),
        tip_paid_total=Coalesce(
            Sum('amount', filter=Q(kind=WorkerPayoutTransaction.Kind.TIP_PAYMENT)),
            Value(Decimal('0')),
        ),
    )
    attendance_minutes = _compute_worker_attendance_minutes(worker, start=start, end=end)
    attendance_hours = _decimal_hours_from_minutes(attendance_minutes)
    hourly_wage = _normalize_decimal(getattr(worker, 'default_hourly_wage', 0))
    if getattr(worker, 'payment_type', '') == WorkerProfile.PaymentType.HOURLY:
        wage_total = (attendance_hours * hourly_wage).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    else:
        wage_total = sum((_job_worker_share_for(job, worker.id) for job in jobs), Decimal('0'))
    tip_total = sum((_job_worker_tip_for(job, worker.id) for job in jobs), Decimal('0'))
    insurance_target_month = _normalize_jalali_month(insurance_month) or _current_jalali_month()
    insurance_start_month = _resolve_worker_insurance_start_month(worker)
    insurance_due_start_month = _jalali_next_month(insurance_start_month)
    insurance_monthly_amount = _normalize_decimal(getattr(worker, 'insurance_amount', 0))
    insurance_cycle_count = _jalali_months_between(insurance_due_start_month, insurance_target_month)
    insurance_total = insurance_monthly_amount * Decimal(str(insurance_cycle_count))
    insurance_paid_total = _insurance_paid_amount_until_month(worker, insurance_target_month)
    insurance_selected_month_paid_total = _insurance_paid_amount_for_month(worker, insurance_target_month)
    payable_total = wage_total + _normalize_decimal(aggregates['bonus_total']) - _normalize_decimal(aggregates['penalty_total']) - _normalize_decimal(aggregates['wage_paid_total'])
    if payable_total < 0:
        payable_total = Decimal('0')
    tip_balance = tip_total - _normalize_decimal(aggregates['tip_paid_total'])
    if tip_balance < 0:
        tip_balance = Decimal('0')
    insurance_balance = insurance_total - _normalize_decimal(insurance_paid_total)
    if insurance_balance < 0:
        insurance_balance = Decimal('0')
    insurance_selected_month_balance = (
        insurance_monthly_amount - insurance_selected_month_paid_total
        if insurance_due_start_month and _jalali_month_lte(insurance_due_start_month, insurance_target_month)
        else Decimal('0')
    )
    if insurance_selected_month_balance < 0:
        insurance_selected_month_balance = Decimal('0')

    return {
        'wage_total': wage_total,
        'attendance_minutes': attendance_minutes,
        'attendance_hours': attendance_hours,
        'hourly_wage': hourly_wage,
        'payment_type': getattr(worker, 'payment_type', ''),
        'tip_total': tip_total,
        'insurance_total': insurance_total,
        'insurance_monthly_amount': insurance_monthly_amount,
        'insurance_cycle_count': insurance_cycle_count,
        'insurance_start_month': insurance_start_month,
        'insurance_due_start_month': insurance_due_start_month,
        'insurance_target_month': insurance_target_month,
        'bonus_total': _normalize_decimal(aggregates['bonus_total']),
        'penalty_total': _normalize_decimal(aggregates['penalty_total']),
        'wage_paid_total': _normalize_decimal(aggregates['wage_paid_total']),
        'tip_paid_total': _normalize_decimal(aggregates['tip_paid_total']),
        'insurance_paid_total': _normalize_decimal(insurance_paid_total),
        'insurance_selected_month_paid_total': _normalize_decimal(insurance_selected_month_paid_total),
        'insurance_selected_month_balance': insurance_selected_month_balance,
        'payable_total': payable_total,
        'tip_balance': tip_balance,
        'insurance_balance': insurance_balance,
        'transactions': transactions.select_related('vehicle_job').order_by('-created_at', '-id'),
    }


def _compute_all_workers_totals(tenant, jobs, insurance_month='', start=None, end=None):
    workers_map = {}
    for job in jobs:
        for worker_id in _job_worker_ids(job):
            if worker_id not in workers_map:
                workers_map[worker_id] = WorkerProfile.objects.select_related('user').filter(
                    id=worker_id,
                    tenant=tenant,
                ).first()
    if tenant:
        # Only hourly workers who actually worked in this range (avoid inflating totals with idle staff).
        hourly_workers = WorkerProfile.objects.select_related('user').filter(
            tenant=tenant,
            payment_type=WorkerProfile.PaymentType.HOURLY,
            is_deleted=False,
            user__is_deleted=False,
        )
        for worker in hourly_workers:
            if worker.id in workers_map:
                continue
            if _compute_worker_attendance_minutes(worker, start=start, end=end) <= 0:
                continue
            workers_map[worker.id] = worker
    workers = [item for item in workers_map.values() if item]
    total_payable = Decimal('0')
    total_bonus = Decimal('0')
    total_penalty = Decimal('0')
    total_insurance = Decimal('0')
    for worker in workers:
        state = _compute_worker_financials(
            worker,
            [job for job in jobs if _job_has_worker(job, worker.id)],
            insurance_month=insurance_month,
            start=start,
            end=end,
        )
        total_payable += state['payable_total']
        total_bonus += state['bonus_total']
        total_penalty += state['penalty_total']
        total_insurance += state['insurance_selected_month_balance']
    return {
        'payable_total': total_payable,
        'bonus_total': total_bonus,
        'penalty_total': total_penalty,
        'insurance_total': total_insurance,
    }


class ReportsDashboardView(APIView):
    @staticmethod
    def _base_queryset(tenant):
        return VehicleEntry.objects.select_related(
            'job',
            'job__assigned_worker',
            'job__assigned_worker__user',
            'customer',
        ).prefetch_related('job__product_lines__product', 'job__service_lines__service', 'payments').filter(
            tenant=tenant,
            status=VehicleEntry.Status.RELEASED,
        )

    @classmethod
    def _build_filtered_vehicles(cls, start, end, query, tenant, worker_id=None, plate_number='', plate_type=''):
        vehicles = cls._base_queryset(tenant)
        if start:
            vehicles = vehicles.filter(released_at__gte=start)
        if end:
            vehicles = vehicles.filter(released_at__lte=end)
        if query:
            vehicles = vehicles.filter(
                Q(driver_name__icontains=query)
                | Q(driver_phone__icontains=query)
                | Q(car_model__icontains=query)
                | Q(plate_number__icontains=query)
                | Q(job__assigned_worker__user__full_name__icontains=query)
                | Q(job__assigned_worker__user__username__icontains=query)
            ).distinct()
        if plate_number:
            vehicles = vehicles.filter(plate_number__icontains=plate_number)
        if plate_type in {'car', 'motorcycle'}:
            vehicles = vehicles.filter(plate_type=plate_type)

        records = list(vehicles.order_by('released_at', 'check_in_at', 'id'))
        if worker_id:
            records = [vehicle for vehicle in records if _job_has_worker(getattr(vehicle, 'job', None), worker_id)]
        return records

    def get(self, request):
        start = _parse_dt(request.query_params.get('start'))
        end = _parse_dt(request.query_params.get('end'), end_of_day=True)
        query = request.query_params.get('q', '').strip()
        plate_number = request.query_params.get('plate_number', '').strip()
        plate_left = request.query_params.get('plate_left', '').strip()
        plate_letter = request.query_params.get('plate_letter', '').strip()
        plate_mid = request.query_params.get('plate_mid', '').strip()
        plate_right = request.query_params.get('plate_right', '').strip()
        plate_type = request.query_params.get('plate_type', '').strip().lower()
        insurance_month = _normalize_jalali_month(request.query_params.get('insurance_month')) or _current_jalali_month()
        if not plate_number:
            plate_parts = [plate_left, plate_letter, plate_mid, plate_right]
            plate_number = ' '.join([part for part in plate_parts if part])
        tenant = getattr(request.user, 'tenant', None)
        worker_id = request.query_params.get('worker_id')
        try:
            worker_id = int(worker_id) if worker_id else None
        except (TypeError, ValueError):
            worker_id = None

        vehicles = self._build_filtered_vehicles(
            start=start,
            end=end,
            query=query,
            tenant=tenant,
            worker_id=worker_id,
            plate_number=plate_number,
            plate_type=plate_type,
        )
        sync_jobs = _query_flag(request.query_params.get('sync'))
        synced_jobs = 0
        if sync_jobs:
            sync_limit = _parse_sync_limit(request.query_params.get('sync_limit'), default=None)
            synced_jobs = _sync_released_jobs(
                (getattr(vehicle, 'job', None) for vehicle in vehicles),
                limit=sync_limit,
            )

        rows = []
        worker_jobs = []
        job_ids = [vehicle.job.id for vehicle in vehicles if getattr(vehicle, 'job', None)]
        adjustment_map = {}
        if job_ids:
            adjustment_rows = (
                WorkerPayoutTransaction.objects
                .filter(tenant=tenant, vehicle_job_id__in=job_ids, kind__in=[
                    WorkerPayoutTransaction.Kind.BONUS,
                    WorkerPayoutTransaction.Kind.PENALTY,
                ])
                .values('vehicle_job_id', 'kind')
                .annotate(total=Coalesce(Sum('amount'), Value(Decimal('0'))))
            )
            for item in adjustment_rows:
                job_id = int(item['vehicle_job_id'])
                if job_id not in adjustment_map:
                    adjustment_map[job_id] = {'bonus_total': Decimal('0'), 'penalty_total': Decimal('0')}
                adjustment_map[job_id][f"{item['kind']}_total"] = _normalize_decimal(item['total'])
        for idx, vehicle in enumerate(vehicles, start=1):
            job = getattr(vehicle, 'job', None)
            if worker_id and job and _job_has_worker(job, worker_id):
                worker_jobs.append(job)
            job_adjustments = adjustment_map.get(job.id if job else 0, {'bonus_total': Decimal('0'), 'penalty_total': Decimal('0')})
            product_names = []
            service_names = []
            if job:
                for line in job.product_lines.all():
                    if line.quantity and line.quantity > 0 and line.product:
                        product_names.append(line.product.name)
                for line in job.service_lines.all():
                    if line.quantity and line.quantity > 0:
                        service_names.append(line.custom_service_name or (line.service.name if line.service else 'خدمت'))
            row = {
                'row': idx,
                'vehicle_id': vehicle.id,
                'driver_name': vehicle.driver_name,
                'driver_gender': vehicle.driver_gender or '',
                'driver_phone': vehicle.driver_phone,
                'car_model': vehicle.car_model,
                'car_color': vehicle.car_color,
                'plate_number': vehicle.plate_number,
                'plate_left': vehicle.plate_left,
                'plate_letter': vehicle.plate_letter,
                'plate_mid': vehicle.plate_mid,
                'plate_right': vehicle.plate_right,
                'plate_type': vehicle.plate_type,
                'status': vehicle.status,
                'carwash_share': float(job.carwash_share_amount) if job else 0,
                'worker_share': float(job.worker_share_amount) if job else 0,
                'bonus_total': float(job_adjustments['bonus_total']),
                'penalty_total': float(job_adjustments['penalty_total']),
                'discount_total': float(_job_discount_total(job)),
                'facility_discount_total': float(_normalize_decimal(getattr(job, 'facility_discount_total', 0))) if job else 0,
                'loyalty_discount_total': float(_normalize_decimal(getattr(job, 'loyalty_discount_total', 0))) if job else 0,
                'manual_discount_total': float(_normalize_decimal(getattr(job, 'manual_discount_total', 0))) if job else 0,
                'tax_total': float(job.tax_total) if job else 0,
                'service_total': float(job.services_total) if job else 0,
                'final_total': float(job.final_total) if job else 0,
                'final_total_without_tip': float(max(Decimal('0'), _normalize_decimal(job.final_total) - _normalize_decimal(job.tip_amount))) if job else 0,
                'before_discount_total': float((_normalize_decimal(job.final_total) + _job_discount_total(job))) if job else 0,
                'tip_amount': float(job.tip_amount) if job else 0,
                'worker_name': _job_worker_names(job),
                'products': ', '.join(product_names),
                'services': ', '.join(service_names),
                'created_at': vehicle.released_at or vehicle.check_in_at,
            }
            rows.append(row)

        if getattr(request.user, 'role', None) == 'worker':
            for row in rows:
                row.pop('driver_gender', None)

        all_jobs = [vehicle.job for vehicle in vehicles if getattr(vehicle, 'job', None)]
        total_carwash = sum((_normalize_decimal(getattr(job, 'carwash_share_amount', 0)) for job in all_jobs), Decimal('0'))
        total_discount = sum((_job_discount_total(job) for job in all_jobs), Decimal('0'))
        total_facility_discount = sum((_normalize_decimal(getattr(job, 'facility_discount_total', 0)) for job in all_jobs), Decimal('0'))
        total_loyalty_discount = sum((_normalize_decimal(getattr(job, 'loyalty_discount_total', 0)) for job in all_jobs), Decimal('0'))
        total_manual_discount = sum((_normalize_decimal(getattr(job, 'manual_discount_total', 0)) for job in all_jobs), Decimal('0'))
        loyalty_discount_count = sum(
            1 for job in all_jobs if _normalize_decimal(getattr(job, 'loyalty_discount_total', 0)) > 0
        )
        total_tax = sum((_normalize_decimal(getattr(job, 'tax_total', 0)) for job in all_jobs), Decimal('0'))
        total_final = sum((_normalize_decimal(getattr(job, 'final_total', 0)) for job in all_jobs), Decimal('0'))
        total_before_discount = total_final + total_discount
        if worker_id:
            total_worker = sum((_job_worker_share_for(job, worker_id) for job in all_jobs), Decimal('0'))
            total_tip = sum((_job_worker_tip_for(job, worker_id) for job in all_jobs), Decimal('0'))
        else:
            total_worker = sum((_normalize_decimal(getattr(job, 'worker_share_amount', 0)) for job in all_jobs), Decimal('0'))
            total_tip = sum((_normalize_decimal(getattr(job, 'tip_amount', 0)) for job in all_jobs), Decimal('0'))
        all_workers_totals = _compute_all_workers_totals(
            tenant,
            all_jobs,
            insurance_month=insurance_month,
            start=start,
            end=end,
        )

        carwash_report = [{
            'row': i + 1,
            'vehicle_id': r['vehicle_id'],
            'driver_name': r['driver_name'],
            'driver_phone': r['driver_phone'],
            'car_model': r['car_model'],
            'car_color': r['car_color'],
            'plate_number': r['plate_number'],
            'plate_left': r['plate_left'],
            'plate_letter': r['plate_letter'],
            'plate_mid': r['plate_mid'],
            'plate_right': r['plate_right'],
            'plate_type': r['plate_type'],
            'carwash_share': r['carwash_share'],
            'worker_name': r['worker_name'],
            'created_at': r['created_at'],
        } for i, r in enumerate(rows)]

        worker_report = []
        for i, r in enumerate(rows):
            job = getattr(vehicles[i], 'job', None)
            row_worker_share = (
                _job_worker_share_for(job, worker_id)
                if worker_id and job
                else _normalize_decimal(r['worker_share'])
            )
            row_final_without_tip = _job_final_total_without_tip(job) if job else Decimal('0')
            row_service_total = (
                _job_share_base_total(job)
                if job
                else _normalize_decimal(r['service_total'])
            )
            row_tip_amount = (
                _job_worker_tip_for(job, worker_id)
                if worker_id and job
                else _normalize_decimal(r['tip_amount'])
            )
            row_commission_percent = _job_worker_commission_percent_for(job) if job else Decimal('0')
            worker_report.append({
                'row': i + 1,
                'vehicle_id': r['vehicle_id'],
                'driver_name': r['driver_name'],
                'driver_phone': r['driver_phone'],
                'car_model': r['car_model'],
                'car_color': r['car_color'],
                'plate_number': r['plate_number'],
                'plate_left': r['plate_left'],
                'plate_letter': r['plate_letter'],
                'plate_mid': r['plate_mid'],
                'plate_right': r['plate_right'],
                'plate_type': r['plate_type'],
                'worker_share': float(row_worker_share),
                'worker_commission_percent': float(row_commission_percent),
                'service_total': float(row_service_total),
                'final_total_without_tip': float(row_final_without_tip),
                'discount_total': r['discount_total'],
                'final_total': r['final_total'],
                'tip_amount': float(row_tip_amount),
                'bonus_total': r['bonus_total'],
                'penalty_total': r['penalty_total'],
                'worker_name': r['worker_name'],
                'created_at': r['created_at'],
            })

        tips_report = [{
            'row': i + 1,
            'vehicle_id': r['vehicle_id'],
            'driver_name': r['driver_name'],
            'driver_phone': r['driver_phone'],
            'car_model': r['car_model'],
            'car_color': r['car_color'],
            'plate_number': r['plate_number'],
            'plate_left': r['plate_left'],
            'plate_letter': r['plate_letter'],
            'plate_mid': r['plate_mid'],
            'plate_right': r['plate_right'],
            'plate_type': r['plate_type'],
            'tip_amount': r['tip_amount'],
            'worker_name': r['worker_name'],
            'products': r['products'],
            'created_at': r['created_at'],
        } for i, r in enumerate(rows)]

        discount_report = []
        for r in rows:
            if (
                _normalize_decimal(r.get('discount_total')) <= 0
                and _normalize_decimal(r.get('loyalty_discount_total')) <= 0
                and _normalize_decimal(r.get('facility_discount_total')) <= 0
                and _normalize_decimal(r.get('manual_discount_total')) <= 0
            ):
                continue
            discount_report.append({
                'row': len(discount_report) + 1,
                'vehicle_id': r['vehicle_id'],
                'driver_name': r['driver_name'],
                'driver_phone': r['driver_phone'],
                'car_model': r['car_model'],
                'car_color': r['car_color'],
                'plate_number': r['plate_number'],
                'plate_left': r['plate_left'],
                'plate_letter': r['plate_letter'],
                'plate_mid': r['plate_mid'],
                'plate_right': r['plate_right'],
                'plate_type': r['plate_type'],
                'facility_discount_total': r['facility_discount_total'],
                'loyalty_discount_total': r['loyalty_discount_total'],
                'manual_discount_total': r['manual_discount_total'],
                'discount_total': r['discount_total'],
                'created_at': r['created_at'],
            })

        revenue_report = []
        revenue_total = Decimal('0')
        for i, vehicle in enumerate(vehicles, start=1):
            payments = list(vehicle.payments.all()) if hasattr(vehicle, 'payments') else []
            payment = payments[0] if payments else None
            if not payment:
                continue
            received_amount = _normalize_decimal(payment.amount) if payment.status == Payment.Status.SUCCESS else Decimal('0')
            outstanding_amount = max(Decimal('0'), _normalize_decimal(payment.amount) - received_amount)
            revenue_total += received_amount
            revenue_report.append({
                'row': len(revenue_report) + 1,
                'vehicle_id': vehicle.id,
                'driver_name': vehicle.driver_name,
                'driver_phone': vehicle.driver_phone,
                'car_model': vehicle.car_model,
                'car_color': vehicle.car_color,
                'plate_number': vehicle.plate_number,
                'plate_left': vehicle.plate_left,
                'plate_letter': vehicle.plate_letter,
                'plate_mid': vehicle.plate_mid,
                'plate_right': vehicle.plate_right,
                'plate_type': vehicle.plate_type,
                'payment_method': payment.method,
                'payment_status': payment.status,
                'service_amount': float(payment.service_amount or 0),
                'product_amount': float(payment.product_amount or 0),
                'discount_amount': float(payment.discount_amount or 0),
                'tip_amount': float(payment.tip_amount or 0),
                'tax_amount': float(
                    getattr(payment, 'tax_amount', 0)
                    or getattr(getattr(vehicle, 'job', None), 'tax_total', 0)
                    or 0
                ),
                'final_total': float(payment.amount or 0),
                'received_amount': float(received_amount),
                'outstanding_amount': float(outstanding_amount),
                'cheque_number': payment.cheque_number,
                'reminder_due_at': payment.reminder_due_at,
                'created_at': payment.created_at,
            })

        attendances = WorkerAttendance.objects.select_related('worker', 'worker__user').filter(
            tenant=tenant,
            worker__is_available=True,
            worker__is_deleted=False,
            worker__user__is_active=True,
            worker__user__is_deleted=False,
        )
        if start:
            attendances = attendances.filter(event_at__gte=start)
        if end:
            attendances = attendances.filter(event_at__lte=end)
        if query:
            attendances = attendances.filter(
                Q(worker__user__full_name__icontains=query) | Q(worker__user__username__icontains=query)
            )
        if worker_id:
            attendances = attendances.filter(worker_id=worker_id)

        attendance_rows = [{
            'row': i,
            'worker_name': _worker_name(event.worker),
            'event_type': event.event_type,
            'event_at': event.event_at,
            'source': event.source,
        } for i, event in enumerate(attendances.order_by('-event_at'), start=1)]

        blocked_plates = BlockedPlate.objects.select_related('blocked_by').filter(tenant=tenant)
        if query:
            blocked_plates = blocked_plates.filter(
                Q(plate_number__icontains=query)
                | Q(note__icontains=query)
                | Q(blocked_by__full_name__icontains=query)
                | Q(blocked_by__username__icontains=query)
            )
        if plate_number:
            blocked_plates = blocked_plates.filter(plate_number__icontains=plate_number)
        if plate_type in {'car', 'motorcycle'}:
            blocked_plates = blocked_plates.filter(plate_type=plate_type)

        blacklist_rows = [{
            'row': index,
            'id': item.id,
            'plate_number': item.plate_number,
            'plate_left': item.plate_left,
            'plate_letter': item.plate_letter,
            'plate_mid': item.plate_mid,
            'plate_right': item.plate_right,
            'plate_type': item.plate_type,
            'note': item.note,
            'blocked_by_name': item.blocked_by.full_name or item.blocked_by.username if item.blocked_by else '-',
            'created_at': item.created_at,
        } for index, item in enumerate(blocked_plates.order_by('-created_at', '-id'), start=1)]

        selected_worker_summary = None
        selected_worker_transactions = []
        if worker_id:
            worker = WorkerProfile.objects.select_related('user').filter(id=worker_id, tenant=tenant).first()
            if worker:
                worker_state = _compute_worker_financials(
                    worker,
                    worker_jobs,
                    insurance_month=insurance_month,
                    start=start,
                    end=end,
                )
                selected_worker_summary = {
                    'worker_id': worker.id,
                    'worker_name': _worker_name(worker),
                    'payment_type': worker_state['payment_type'],
                    'default_commission_percent': float(worker.default_commission_percent or 0),
                    'attendance_minutes': int(worker_state['attendance_minutes']),
                    'attendance_hours': float(worker_state['attendance_hours']),
                    'hourly_wage': float(worker_state['hourly_wage']),
                    'wage_total': float(worker_state['wage_total']),
                    'tip_total': float(worker_state['tip_total']),
                    'insurance_total': float(worker_state['insurance_total']),
                    'insurance_monthly_amount': float(worker_state['insurance_monthly_amount']),
                    'insurance_cycle_count': int(worker_state['insurance_cycle_count']),
                    'bonus_total': float(worker_state['bonus_total']),
                    'penalty_total': float(worker_state['penalty_total']),
                    'wage_paid_total': float(worker_state['wage_paid_total']),
                    'tip_paid_total': float(worker_state['tip_paid_total']),
                    'insurance_paid_total': float(worker_state['insurance_paid_total']),
                    'insurance_selected_month_paid_total': float(worker_state['insurance_selected_month_paid_total']),
                    'insurance_selected_month_balance': float(worker_state['insurance_selected_month_balance']),
                    'payable_total': float(worker_state['payable_total']),
                    'tip_balance': float(worker_state['tip_balance']),
                    'insurance_balance': float(worker_state['insurance_balance']),
                    'insurance_month': worker_state['insurance_target_month'],
                    'insurance_start_month': worker_state['insurance_start_month'],
                    'insurance_due_start_month': worker_state['insurance_due_start_month'],
                }
                selected_worker_transactions = [
                    {
                        'id': tx.id,
                        'kind': tx.kind,
                        'amount': float(tx.amount or 0),
                        'note': tx.note,
                        'vehicle_job_id': tx.vehicle_job_id,
                        'reference_month': tx.reference_month,
                        'created_at': tx.created_at,
                    }
                    for tx in worker_state['transactions'][:100]
                ]
                # Keep top KPI cards synced with the selected worker (not all co-workers / hourly staff).
                total_worker = worker_state['wage_total']
                total_tip = worker_state['tip_total']
                all_workers_totals = {
                    'payable_total': worker_state['payable_total'],
                    'bonus_total': worker_state['bonus_total'],
                    'penalty_total': worker_state['penalty_total'],
                    'insurance_total': worker_state['insurance_selected_month_balance'],
                }

        return Response({
            'filters': {
                'start': request.query_params.get('start'),
                'end': request.query_params.get('end'),
                'q': query,
                'worker_id': worker_id,
                'plate_number': plate_number,
                'plate_left': plate_left,
                'plate_letter': plate_letter,
                'plate_mid': plate_mid,
                'plate_right': plate_right,
                'plate_type': plate_type,
                'insurance_month': insurance_month,
                'sync': sync_jobs,
                'sync_limit': _parse_sync_limit(request.query_params.get('sync_limit'), default=None),
            },
            'synced_jobs': synced_jobs,
            'summary': {
                'vehicles_count': len(rows),
                'carwash_total': float(total_carwash),
                'worker_total': float(total_worker),
                'tips_total': float(total_tip),
                'discount_total': float(total_discount),
                'facility_discount_total': float(total_facility_discount),
                'loyalty_discount_total': float(total_loyalty_discount),
                'manual_discount_total': float(total_manual_discount),
                'loyalty_discount_count': int(loyalty_discount_count),
                'tax_total': float(total_tax),
                'final_total': float(total_final),
                'before_discount_total': float(total_before_discount),
                'payable_worker_total': float(all_workers_totals['payable_total']),
                'insurance_total': float(all_workers_totals['insurance_total']),
                'payable_tip_total': float(selected_worker_summary['tip_balance']) if selected_worker_summary else 0,
                'bonus_total': float(all_workers_totals['bonus_total']),
                'penalty_total': float(all_workers_totals['penalty_total']),
            },
            'section_totals': {
                'overall': {
                    'vehicles_count': len(rows),
                    'carwash_total': float(total_carwash),
                    'worker_total': float(total_worker),
                    'tips_total': float(total_tip),
                    'discount_total': float(total_discount),
                    'facility_discount_total': float(total_facility_discount),
                    'loyalty_discount_total': float(total_loyalty_discount),
                    'manual_discount_total': float(total_manual_discount),
                    'loyalty_discount_count': int(loyalty_discount_count),
                    'tax_total': float(total_tax),
                    'final_total': float(total_final),
                    'before_discount_total': float(total_before_discount),
                },
                'carwash': {'carwash_total': float(total_carwash)},
                'worker': {
                    'worker_total': float(total_worker),
                    'payable_total': float(all_workers_totals['payable_total']),
                    'insurance_total': float(all_workers_totals['insurance_total']),
                    'bonus_total': float(all_workers_totals['bonus_total']),
                    'penalty_total': float(all_workers_totals['penalty_total']),
                },
                'tips': {'tips_total': float(total_tip)},
                'discount': {
                    'discount_total': float(total_discount),
                    'facility_discount_total': float(total_facility_discount),
                    'loyalty_discount_total': float(total_loyalty_discount),
                    'manual_discount_total': float(total_manual_discount),
                    'loyalty_discount_count': int(loyalty_discount_count),
                    'count': len(discount_report),
                },
                'attendance': {'count': len(attendance_rows)},
                'blacklist': {'count': len(blacklist_rows)},
                'revenue': {'revenue_total': float(revenue_total), 'count': len(revenue_report)},
            },
            'overall_report': rows,
            'carwash_report': carwash_report,
            'worker_report': worker_report,
            'tips_report': tips_report,
            'discount_report': discount_report,
            'attendance_report': attendance_rows,
            'blacklist_report': blacklist_rows,
            'revenue_report': revenue_report,
            'selected_worker_summary': selected_worker_summary,
            'selected_worker_transactions': selected_worker_transactions,
        })


class ReportsExportView(APIView):
    def get(self, request):
        tab_key = str(request.query_params.get('tab') or 'overall').strip().lower()
        config = _build_export_config(tab_key)
        headers = list(config['headers'])
        if getattr(request.user, 'role', None) == 'worker':
            headers = [item for item in headers if item[0] != 'driver_gender']
        dashboard_response = ReportsDashboardView().get(request)
        payload = getattr(dashboard_response, 'data', {}) or {}
        rows = payload.get(config['rows_key'], []) or []

        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="{config["filename"]}.csv"'
        writer = csv.writer(response)
        writer.writerow([label for _field, label in headers])
        for row in rows:
            writer.writerow([_export_row_value(row, field) for field, _label in headers])
        return response


class ReportsWorkerPayoutView(APIView):
    def post(self, request):
        tenant = getattr(request.user, 'tenant', None)
        worker_id = request.data.get('worker_id')
        mode = str(request.data.get('mode', 'full')).strip().lower()
        payout_target = str(request.data.get('payout_target', 'wage')).strip().lower()
        note = str(request.data.get('note', '')).strip()
        try:
            worker_id = int(worker_id)
        except (TypeError, ValueError):
            return Response({'worker_id': ['Invalid worker.']}, status=status.HTTP_400_BAD_REQUEST)
        if mode not in {'full', 'partial'}:
            return Response({'mode': ['Invalid mode.']}, status=status.HTTP_400_BAD_REQUEST)
        if payout_target not in {'wage', 'tip', 'insurance'}:
            return Response({'payout_target': ['Invalid payout target.']}, status=status.HTTP_400_BAD_REQUEST)
        insurance_month = _normalize_jalali_month(request.data.get('insurance_month'))

        worker = WorkerProfile.objects.select_related('user').filter(id=worker_id, tenant=tenant).first()
        if not worker:
            return Response({'worker_id': ['Worker not found.']}, status=status.HTTP_404_NOT_FOUND)

        jobs = _get_worker_jobs(tenant, worker_id)
        if payout_target == 'insurance' and not insurance_month:
            return Response({'insurance_month': ['ماه بیمه معتبر نیست.']}, status=status.HTTP_400_BAD_REQUEST)
        worker_state = _compute_worker_financials(worker, jobs, insurance_month=insurance_month)
        if payout_target == 'insurance':
            insurance_due_start_month = worker_state['insurance_due_start_month']
            if not insurance_due_start_month or not _jalali_month_lte(insurance_due_start_month, insurance_month):
                return Response({'insurance_month': ['مانده حق بیمه از ماه بعد از شروع همکاری نیرو محاسبه می‌شود.']}, status=status.HTTP_400_BAD_REQUEST)
            payable_total = worker_state['insurance_selected_month_balance']
            if payable_total <= 0:
                return Response({'detail': f'این ماه قبلا تسویه شده است: {insurance_month}.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            payable_total = worker_state['tip_balance'] if payout_target == 'tip' else worker_state['payable_total']
            if payable_total <= 0:
                return Response({'detail': 'مانده‌ای برای پرداخت وجود ندارد.' if payout_target == 'tip' else 'مانده حقوقی برای پرداخت وجود ندارد.'}, status=status.HTTP_400_BAD_REQUEST)

        if mode == 'full':
            amount = payable_total
        else:
            amount = _normalize_decimal(request.data.get('amount'))
            if amount <= 0:
                return Response({'amount': ['مبلغ باید بیشتر از صفر باشد.']}, status=status.HTTP_400_BAD_REQUEST)
            if amount >= payable_total:
                return Response({'amount': ['مبلغ باید کمتر از مانده کل باشد.']}, status=status.HTTP_400_BAD_REQUEST)

        tx = WorkerPayoutTransaction.objects.create(
            tenant=tenant,
            worker=worker,
            kind=(
                WorkerPayoutTransaction.Kind.TIP_PAYMENT if payout_target == 'tip'
                else WorkerPayoutTransaction.Kind.INSURANCE_PAYMENT if payout_target == 'insurance'
                else WorkerPayoutTransaction.Kind.WAGE_PAYMENT
            ),
            reference_month=insurance_month if payout_target == 'insurance' else '',
            amount=amount,
            note=note or (
                'پرداخت کامل انعام' if payout_target == 'tip' and mode == 'full'
                else 'پرداخت بخشی از انعام' if payout_target == 'tip'
                else f'پرداخت کامل حق بیمه {insurance_month}' if payout_target == 'insurance' and mode == 'full'
                else f'پرداخت بخشی از حق بیمه {insurance_month}' if payout_target == 'insurance'
                else 'پرداخت کامل حقوق' if mode == 'full'
                else 'پرداخت بخشی از حقوق'
            ),
            created_by=request.user if getattr(request.user, 'is_authenticated', False) else None,
        )

        remaining = payable_total - amount
        if remaining < 0:
            remaining = Decimal('0')
        return Response({
            'detail': 'پرداخت انعام ثبت شد.' if payout_target == 'tip' else 'پرداخت حق بیمه ثبت شد.' if payout_target == 'insurance' else 'پرداخت حقوق ثبت شد.',
            'transaction_id': tx.id,
            'paid_amount': float(amount),
            'remaining_payable': float(remaining),
            'payout_target': payout_target,
            'insurance_month': insurance_month,
        })


class ReportsWorkerAdjustmentView(APIView):
    def post(self, request):
        tenant = getattr(request.user, 'tenant', None)
        worker_id = request.data.get('worker_id')
        vehicle_job_id = request.data.get('vehicle_job_id')
        kind = str(request.data.get('kind', '')).strip().lower()
        note = str(request.data.get('note', '')).strip()
        amount = _normalize_decimal(request.data.get('amount'))

        try:
            worker_id = int(worker_id)
        except (TypeError, ValueError):
            return Response({'worker_id': ['Invalid worker.']}, status=status.HTTP_400_BAD_REQUEST)
        if kind not in {WorkerPayoutTransaction.Kind.BONUS, WorkerPayoutTransaction.Kind.PENALTY}:
            return Response({'kind': ['Invalid adjustment kind.']}, status=status.HTTP_400_BAD_REQUEST)
        if amount <= 0:
            return Response({'amount': ['مبلغ باید بیشتر از صفر باشد.']}, status=status.HTTP_400_BAD_REQUEST)

        worker = WorkerProfile.objects.select_related('user').filter(id=worker_id, tenant=tenant).first()
        if not worker:
            return Response({'worker_id': ['Worker not found.']}, status=status.HTTP_404_NOT_FOUND)

        vehicle_job = None
        if vehicle_job_id:
            vehicle_job = VehicleJob.objects.filter(id=vehicle_job_id, tenant=tenant).first()

        if kind == WorkerPayoutTransaction.Kind.PENALTY:
            jobs = _get_worker_jobs(tenant, worker_id)
            worker_state = _compute_worker_financials(worker, jobs)
            amount = min(amount, worker_state['payable_total'])

        tx = WorkerPayoutTransaction.objects.create(
            tenant=tenant,
            worker=worker,
            vehicle_job=vehicle_job,
            kind=kind,
            amount=amount,
            note=note,
            created_by=request.user if getattr(request.user, 'is_authenticated', False) else None,
        )
        return Response({
            'detail': 'تعدیل حقوق ثبت شد.',
            'transaction_id': tx.id,
            'amount': float(amount),
            'kind': kind,
        }, status=status.HTTP_201_CREATED)


class ReportsPayoutSettleView(APIView):
    def post(self, request):
        return Response(
            {'detail': 'این endpoint منسوخ شده است. از /reports/workers/payouts/ استفاده کنید.'},
            status=status.HTTP_410_GONE,
        )
