import json
import logging
import math
import threading
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from urllib import error as urllib_error
from urllib import request as urllib_request

from django.conf import settings
from django.db import close_old_connections, transaction
from django.db.models import Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

logger = logging.getLogger(__name__)

from apps.services.models import (
    DEFAULT_SMS_VEHICLE_ASSIGNED_INVOICE_TEMPLATE,
    DEFAULT_SMS_VEHICLE_ASSIGNED_TEMPLATE,
    DEFAULT_SMS_VEHICLE_RELEASED_TEMPLATE,
    GeneralSettings,
    normalize_vehicle_released_sms_template,
)
from apps.vehicles.models import VehicleEntry
from apps.vehicles.loyalty import loyalty_discount_mode, next_fixed_discount_notice


PERSIAN_DIGITS = '۰۱۲۳۴۵۶۷۸۹'
ARABIC_DIGITS = '٠١٢٣٤٥٦٧٨٩'


def sms_chars_per_segment():
    """Single-part UCS-2 limit (Melipayamak/IranPayamak Persian SMS = 70)."""
    return max(1, int(getattr(settings, 'SMS_CHARS_PER_SEGMENT', 70) or 70))


def sms_chars_per_multipart_segment():
    """
    Multipart UCS-2 uses UDH overhead (typically 3 chars), so 67 when single is 70.
    Melipayamak bills long Persian messages in these chunks.
    """
    single = sms_chars_per_segment()
    return max(1, single - 3)


def sms_price_per_segment():
    return Decimal(str(getattr(settings, 'SMS_PRICE_PER_SEGMENT', 185) or 185))


def sms_provider_footer_text():
    """
    IranPayamak often appends an unsubscribe footer (e.g. لغو11) to delivered SMS.
    Include it in billable length so wallet debit matches provider panel parts.
    """
    configured = getattr(settings, 'SMS_PROVIDER_FOOTER', None)
    if configured is None:
        return '\nلغو11'
    return str(configured)


def sms_billable_text(text):
    body = str(text or '')
    if not body.strip():
        return ''
    footer = sms_provider_footer_text()
    if not footer:
        return body
    if 'لغو' in body:
        return body
    return f'{body}{footer}'


def sms_segments_for_text(text):
    """
    Count Melipayamak-style parts from the exact message that will be billed.
    Not a flat fee: each send is measured by its own character length.
    """
    length = len(sms_billable_text(text))
    if length <= 0:
        return 0
    single_limit = sms_chars_per_segment()
    if length <= single_limit:
        return 1
    return math.ceil(length / sms_chars_per_multipart_segment())


def sms_cost_for_text(text):
    segments = sms_segments_for_text(text)
    if segments <= 0:
        return Decimal('0')
    return sms_price_per_segment() * Decimal(segments)

DEFAULT_SMS_TEMPLATES = [
    {
        'code': 'welcome',
        'title': 'خوش‌آمدگویی',
        'body': 'سلام [نام مشتری] عزیز، از همراهی شما با [نام کارواش] متشکریم.',
        'display_order': 10,
    },
    {
        'code': 'discount',
        'title': 'تخفیف وفاداری',
        'body': '[نام مشتری] عزیز، برای مراجعه بعدی شما در [نام کارواش] تخفیف ویژه فعال شد.',
        'display_order': 20,
    },
    {
        'code': 'reminder',
        'title': 'یادآوری مراجعه',
        'body': 'سلام [نام مشتری] عزیز، مدت زیادی از آخرین مراجعه شما به [نام کارواش] گذشته است.',
        'display_order': 30,
    },
]


PERSIAN_NUMBER_TRANSLATION = str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')


def make_json_safe(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): make_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [make_json_safe(item) for item in value]
    return value


def to_english_digits(value):
    translated = []
    for char in str(value or ''):
        if char in PERSIAN_DIGITS:
            translated.append(str(PERSIAN_DIGITS.index(char)))
        elif char in ARABIC_DIGITS:
            translated.append(str(ARABIC_DIGITS.index(char)))
        else:
            translated.append(char)
    return ''.join(translated)


def normalize_phone(value):
    raw = to_english_digits(value).strip()
    digits = ''.join(char for char in raw if char.isdigit())
    if digits.startswith('98') and len(digits) == 12:
        digits = f'0{digits[2:]}'
    return digits


def is_valid_iran_mobile(value):
    phone = normalize_phone(value)
    return len(phone) == 11 and phone.startswith('09')


def to_persian_digits(value):
    return str(value or '').translate(PERSIAN_NUMBER_TRANSLATION)


def format_toman(value):
    amount = int(round(float(value or 0)))
    return f"{to_persian_digits(f'{amount:,}'.replace(',', '،'))} تومان"


def _decimal_value(value):
    return Decimal(str(value or 0))


def gregorian_to_jalali(date_obj):
    gy = int(date_obj.year) - 1600
    gm = int(date_obj.month) - 1
    gd = int(date_obj.day) - 1
    g_days_in_month = [31, 29 if ((date_obj.year % 4 == 0 and date_obj.year % 100 != 0) or (date_obj.year % 400 == 0)) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
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
    jd = j_day_no + 1
    return jy, jm + 1, jd


def format_jalali_date(value):
    if not value:
        return '-'
    localized = timezone.localtime(value) if hasattr(value, 'tzinfo') and value.tzinfo else value
    jy, jm, jd = gregorian_to_jalali(localized.date())
    return to_persian_digits(f'{jy:04d}/{jm:02d}/{jd:02d}')


def format_local_time(value):
    if not value:
        return '-'
    localized = timezone.localtime(value) if hasattr(value, 'tzinfo') and value.tzinfo else value
    return to_persian_digits(localized.strftime('%H:%M'))


def customer_display_name(name):
    normalized = str(name or '').strip()
    if normalized in {'', '1111', 'مشتری بدون نام'}:
        return ''
    return normalized


def customer_title(gender=''):
    normalized = str(gender or '').strip().lower()
    if normalized == 'male':
        return 'آقای'
    if normalized == 'female':
        return 'خانم'
    return ''


def customer_display_name_with_title(name, gender=''):
    normalized = customer_display_name(name)
    title = customer_title(gender)
    if normalized and title:
        return f'{title} {normalized}'
    return normalized


def customer_greeting(name, gender=''):
    normalized = customer_display_name_with_title(name, gender)
    return f'{normalized} عزیز' if normalized else 'مشتری عزیز'


def iter_service_lines(job):
    if not job:
        return []
    service_lines = getattr(job, 'service_lines', None)
    if hasattr(service_lines, 'all'):
        return list(service_lines.all())
    if isinstance(service_lines, list):
        return service_lines
    return []


def format_plate_for_sms(vehicle):
    if not vehicle:
        return 'بدون پلاک'
    plate_type = str(getattr(vehicle, 'plate_type', '') or '').strip()
    left = str(getattr(vehicle, 'plate_left', '') or '').strip()
    letter = str(getattr(vehicle, 'plate_letter', '') or '').strip()
    mid = str(getattr(vehicle, 'plate_mid', '') or '').strip()
    right = str(getattr(vehicle, 'plate_right', '') or '').strip()
    if plate_type == 'motorcycle':
        if mid and letter:
            return f'{letter} - {mid}'
        return str(getattr(vehicle, 'plate_number', '') or '').strip() or 'بدون پلاک'
    if right and mid and letter and left:
        return f'{right} - {mid} {letter} {left}'
    raw_parts = str(getattr(vehicle, 'plate_number', '') or '').strip().split()
    if len(raw_parts) >= 4:
        return f'{raw_parts[3]} - {raw_parts[2]} {raw_parts[1]} {raw_parts[0]}'
    return str(getattr(vehicle, 'plate_number', '') or '').strip() or 'بدون پلاک'


def refresh_vehicle_for_sms(vehicle):
    vehicle_id = getattr(vehicle, 'pk', None) or getattr(vehicle, 'id', None)
    if not vehicle_id:
        return vehicle
    return (
        VehicleEntry.objects.select_related('tenant', 'job')
        .prefetch_related('job__service_lines__service', 'job__product_lines__product')
        .filter(pk=vehicle_id)
        .first()
        or vehicle
    )


def assignment_discount_total(job):
    if not job:
        return Decimal('0')
    for field in ('total_discount', 'discount_total'):
        value = _decimal_value(getattr(job, field, 0))
        if value > 0:
            return value
    discount_total = (
        _decimal_value(getattr(job, 'facility_discount_total', 0))
        + _decimal_value(getattr(job, 'loyalty_discount_total', 0))
        + _decimal_value(getattr(job, 'manual_discount_total', 0))
    )
    if discount_total > 0:
        return discount_total
    return sum((_decimal_value(getattr(line, 'discount_amount', 0)) for line in iter_service_lines(job)), Decimal('0'))


def _service_line_list_total(line):
    quantity = _decimal_value(getattr(line, 'quantity', 1)) or Decimal('1')
    list_unit_price = _decimal_value(getattr(line, 'list_unit_price', 0))
    if list_unit_price > 0:
        return list_unit_price * quantity
    return _decimal_value(getattr(line, 'line_total', 0)) + _decimal_value(getattr(line, 'discount_amount', 0))


def assignment_invoice_total(job):
    if not job:
        return Decimal('0')
    service_list_subtotal = _decimal_value(getattr(job, 'service_list_subtotal', 0))
    products_total = _decimal_value(getattr(job, 'products_total', 0))
    if service_list_subtotal > 0:
        return service_list_subtotal + products_total
    line_total = Decimal('0')
    for line in iter_service_lines(job):
        line_total += _service_line_list_total(line)
    if line_total > 0 or products_total > 0:
        return line_total + products_total
    services_total = _decimal_value(getattr(job, 'services_total', 0))
    discount_total = assignment_discount_total(job)
    if services_total > 0 or products_total > 0 or discount_total > 0:
        return services_total + products_total + discount_total
    return _decimal_value(getattr(job, 'final_total', 0))


def assignment_invoice_final_total(job):
    if not job:
        return Decimal('0')
    final_total = _decimal_value(getattr(job, 'final_total', 0))
    if final_total > 0:
        return final_total
    total = assignment_invoice_total(job) - assignment_discount_total(job) + assignment_tax_total(job)
    return total if total > 0 else Decimal('0')


def assignment_tax_total(job):
    if not job:
        return Decimal('0')
    stored = _decimal_value(getattr(job, 'tax_total', 0))
    if stored > 0:
        return stored
    return Decimal('0')


def build_services_sms_summary(job):
    lines = []
    for line in iter_service_lines(job):
        title = str(
            getattr(line, 'custom_service_name', '')
            or getattr(getattr(line, 'service', None), 'name', '')
            or getattr(line, 'service_name', '')
            or 'خدمت'
        ).strip()
        amount = _service_line_list_total(line)
        if amount <= 0:
            amount = _decimal_value(getattr(line, 'line_total', 0))
        if amount > 0:
            lines.append(f'{title} : {format_toman(amount)}')
        else:
            lines.append(title)
    for line in iter_product_lines(job):
        product = getattr(line, 'product', None)
        title = str(
            getattr(product, 'name', '')
            or getattr(line, 'product_name', '')
            or 'قلم فروشگاهی'
        ).strip()
        quantity = _decimal_value(getattr(line, 'quantity', 0))
        amount = _decimal_value(getattr(line, 'line_total', 0))
        if amount <= 0:
            amount = _decimal_value(getattr(line, 'unit_price', 0)) * (quantity or Decimal('1'))
        qty_label = to_persian_digits(str(int(quantity))) if quantity > 0 else ''
        prefix = f'{title} × {qty_label}' if qty_label else title
        if amount > 0:
            lines.append(f'{prefix} : {format_toman(amount)}')
        else:
            lines.append(prefix)
    return '\n'.join(lines) if lines else 'خدمات ثبت شده است: مبلغ هنگام نهایی‌سازی اعلام می‌شود'


def iter_product_lines(job):
    if not job:
        return []
    if hasattr(job, 'product_lines'):
        manager = job.product_lines
        if hasattr(manager, 'all'):
            return list(manager.all())
        if isinstance(manager, (list, tuple)):
            return list(manager)
    return list(getattr(job, 'product_lines', []) or [])


def normalize_assignment_sms_wording(template):
    text = str(template or '').replace('[خطاب مشتری]', '[نام مشتری]')
    replacements = {
        'شماره پذیرش: [شماره پذیرش]\nخودروی شما با پلاک [پلاک]،': 'خودروی شما با\nشماره پذیرش: [شماره پذیرش] با پلاک [پلاک]،',
        'شماره پذیرش: [شماره پذیرش]\nخودروی شما با پلاک [پلاک]': 'خودروی شما با\nشماره پذیرش: [شماره پذیرش] با پلاک [پلاک]',
        'با پلاک [پلاک] در ساعت': 'با پلاک [پلاک]، در ساعت',
        '[ساعت تخصیص] روز': '[ساعت تخصیص]، روز',
        '[تاریخ تخصیص]، در کارواش': '[تاریخ تخصیص] در مجموعه کارواش',
        '[تاریخ تخصیص] در کارواش': '[تاریخ تخصیص] در مجموعه کارواش',
        'برای انجام خدمات ثبت و تخصیص داده شد': 'برای انجام خدمات، پذیرش شد',
        'برای انجام خدمات، ثبت و تخصیص داده شد': 'برای انجام خدمات، پذیرش شد',
        'تخصیص داده شد': 'پذیرش شد',
        'پیش فاکتور خدمات:': 'خدمات:',
        'پیش‌فاکتور خدمات:': 'خدمات:',
        'مبلغ نهایی بعد از تخفیف:': 'مبلغ نهایی:',
        '1 ساعت کاری': '30 دقیقه',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    if '[خلاصه خدمات]' in text and '---------------' not in text:
        text = text.replace('[خلاصه خدمات]\n', '[خلاصه خدمات]\n---------------\n')
    return text


def order_assignment_financial_lines(text):
    lines = str(text or '').splitlines()
    services_index = next((index for index, line in enumerate(lines) if '[خلاصه خدمات]' in line), -1)
    if services_index < 0:
        return '\n'.join(lines)

    financial_lines = {'total': None, 'discount': None, 'tax': None, 'final': None}
    remaining = []
    for line in lines:
        if '[جمع کل]' in line or '[جمع نرخ نامه]' in line:
            financial_lines['total'] = line
        elif '[جمع تخفیف]' in line:
            financial_lines['discount'] = line
        elif '[مالیات]' in line:
            financial_lines['tax'] = line
        elif '[مبلغ نهایی]' in line:
            financial_lines['final'] = line
        else:
            remaining.append(line)

    services_index = next((index for index, line in enumerate(remaining) if '[خلاصه خدمات]' in line), -1)
    insert_at = services_index + 1
    if insert_at < len(remaining) and remaining[insert_at].strip() == '---------------':
        insert_at += 1

    ordered_financials = [line for line in (
        financial_lines['total'],
        financial_lines['discount'],
        financial_lines['tax'],
        financial_lines['final'],
    ) if line]
    remaining[insert_at:insert_at] = ordered_financials
    return '\n'.join(remaining)


def normalize_vehicle_assignment_sms_template(template):
    text = normalize_assignment_sms_wording(template).strip()
    if not text:
        return text
    lines = text.splitlines()
    if '[شماره پذیرش]' not in text:
        lines.insert(1 if lines else 0, 'شماره پذیرش: [شماره پذیرش]')
        text = '\n'.join(lines)
    insertions = []
    if '[خلاصه خدمات]' not in text:
        insertions.append('خدمات:')
        insertions.append('[خلاصه خدمات]')
        insertions.append('---------------')
    if '[جمع کل]' not in text and '[جمع نرخ نامه]' not in text:
        insertions.append('جمع کل: [جمع کل]')
    if '[جمع تخفیف]' not in text:
        insertions.append('تخفیف این سفارش: [جمع تخفیف]')
    if '[مالیات]' not in text:
        insertions.append('مالیات: [مالیات]')
    if '[مبلغ نهایی]' not in text:
        insertions.append('مبلغ نهایی: [مبلغ نهایی]')
    if 'از اعتماد شما سپاسگزاریم' not in text:
        insertions.append('از اعتماد شما سپاسگزاریم')
    if not insertions:
        return order_assignment_financial_lines(text)
    anchor_index = next((index for index, line in enumerate(lines) if '[جمع کل]' in line or '[جمع نرخ نامه]' in line), -1)
    insert_at = anchor_index + 1 if anchor_index >= 0 else len(lines)
    lines[insert_at:insert_at] = insertions
    return order_assignment_financial_lines('\n'.join(lines))


def render_template_tokens(template_text, context):
    """Replace tokens longest-first so [تعداد مراجعه] cannot corrupt [تعداد مراجعات]."""
    message = str(template_text or '').strip()
    if not message or not context:
        return message
    for token in sorted(context.keys(), key=lambda item: (-len(str(item)), str(item))):
        message = message.replace(str(token), str(context[token]))
    return message


def resolve_vehicle_visit_count(vehicle, visit_count=None):
    if visit_count is not None:
        try:
            return max(0, int(visit_count or 0))
        except (TypeError, ValueError):
            return 0
    tenant = getattr(vehicle, 'tenant', None)
    if tenant is None or not getattr(tenant, 'pk', None):
        return 0
    from apps.vehicles.loyalty import get_or_create_plate_loyalty, loyalty_snapshot

    profile = get_or_create_plate_loyalty(
        tenant=tenant,
        plate_number=getattr(vehicle, 'plate_number', ''),
        plate_left=getattr(vehicle, 'plate_left', ''),
        plate_letter=getattr(vehicle, 'plate_letter', ''),
        plate_mid=getattr(vehicle, 'plate_mid', ''),
        plate_right=getattr(vehicle, 'plate_right', ''),
    )
    return int(loyalty_snapshot(profile).get('visit_count', 0) or 0)


def _format_score_label(score):
    return to_persian_digits(str(round(float(score or 0), 1)).replace('.0', ''))


def _format_percent_label(percent):
    return f"{to_persian_digits(str(round(float(percent or 0), 2)).replace('.0', ''))}٪"


def build_vehicle_sms_token_context(
    vehicle,
    *,
    assigned_at=None,
    released_at=None,
    visit_count=None,
    customer_score=None,
    next_discount_percent=None,
    final_total=None,
    discount_total=None,
    tip_amount=None,
    facility_discount_total=None,
    loyalty_discount_total=None,
    manual_discount_total=None,
    tax_total=None,
    settings_obj=None,
):
    """
    Shared token map for assignment + release templates.
    Stage-specific tokens stay empty until that stage has a value.
    """
    assigned_at = assigned_at or getattr(vehicle, 'ready_at', None) or getattr(vehicle, 'entered_at', None) or getattr(vehicle, 'updated_at', None)
    released_at = released_at or getattr(vehicle, 'released_at', None)
    job = getattr(vehicle, 'job', None)
    plate_label = format_plate_for_sms(vehicle)
    driver_gender = getattr(vehicle, 'driver_gender', '') or getattr(getattr(vehicle, 'customer', None), 'gender', '')
    resolved_visit_count = resolve_vehicle_visit_count(vehicle, visit_count)
    visit_count_label = to_persian_digits(str(resolved_visit_count))

    resolved_score = customer_score
    if resolved_score is None:
        resolved_score = getattr(vehicle, 'loyalty_score_snapshot', None)
        if resolved_score is None:
            resolved_score = 0
    resolved_loyalty_percent = getattr(vehicle, 'loyalty_discount_percent_snapshot', None)
    if resolved_loyalty_percent is None:
        resolved_loyalty_percent = 0
    next_percent = Decimal(str(next_discount_percent if next_discount_percent is not None else 0))
    next_discount_label = _format_percent_label(next_percent)
    mode = loyalty_discount_mode(settings_obj) if settings_obj is not None else 'step'
    fixed_discount_notice = (
        next_fixed_discount_notice(settings_obj, resolved_visit_count)
        if mode == 'fixed'
        else None
    )
    if mode == 'fixed':
        next_discount_sms_value = to_persian_digits(fixed_discount_notice.get('text')) if fixed_discount_notice else ''
    else:
        next_discount_sms_value = next_discount_label

    resolved_tip = tip_amount if tip_amount is not None else getattr(job, 'tip_amount', 0)
    resolved_facility = (
        facility_discount_total
        if facility_discount_total is not None
        else getattr(job, 'facility_discount_total', 0)
    )
    resolved_loyalty = (
        loyalty_discount_total
        if loyalty_discount_total is not None
        else getattr(job, 'loyalty_discount_total', 0)
    )
    resolved_manual = (
        manual_discount_total
        if manual_discount_total is not None
        else getattr(job, 'manual_discount_total', 0)
    )
    resolved_discount = discount_total if discount_total is not None else assignment_discount_total(job)
    resolved_tax = tax_total if tax_total is not None else assignment_tax_total(job)
    if _decimal_value(resolved_tax) <= 0:
        resolved_tax = assignment_tax_total(job)
    resolved_final = final_total if final_total is not None else assignment_invoice_final_total(job)
    list_total = assignment_invoice_total(job)

    return {
        '[نام مشتری]': customer_display_name_with_title(getattr(vehicle, 'driver_name', ''), driver_gender) or 'مشتری',
        '[خطاب مشتری]': customer_greeting(getattr(vehicle, 'driver_name', ''), driver_gender),
        '[جنسیت مشتری]': customer_title(driver_gender),
        '[نام کارواش]': getattr(getattr(vehicle, 'tenant', None), 'name', '') or 'کارواش',
        '[شماره پذیرش]': to_persian_digits(getattr(vehicle, 'admission_number', None) or getattr(vehicle, 'id', '') or ''),
        '[پلاک]': plate_label,
        '[مدل خودرو]': getattr(vehicle, 'car_model', '') or '',
        '[نام ماشین]': getattr(vehicle, 'car_model', '') or '',
        '[ساعت تخصیص]': format_local_time(assigned_at) if assigned_at else '',
        '[تاریخ تخصیص]': format_jalali_date(assigned_at) if assigned_at else '',
        '[ساعت ترخیص]': format_local_time(released_at) if released_at else '',
        '[تاریخ ترخیص]': format_jalali_date(released_at) if released_at else '',
        '[خلاصه خدمات]': build_services_sms_summary(job),
        '[جمع کل]': format_toman(list_total),
        '[جمع نرخ نامه]': format_toman(list_total),
        '[امتیاز مشتری]': _format_score_label(resolved_score),
        '[درصد تخفیف سفارش بعد]': next_discount_sms_value,
        '[درصد تخفیف مراجعه بعد]': next_discount_sms_value,
        '[درصد تخفیف امتیاز مشتری]': _format_percent_label(resolved_loyalty_percent or next_percent),
        '[تعداد مراجعات]': visit_count_label,
        '[تعداد مراجعه]': visit_count_label,
        '[تعداد مراجعه مانده تا تخفیف]': (
            to_persian_digits(str(fixed_discount_notice.get('remaining_visits', 0)))
            if fixed_discount_notice
            else '۰'
        ),
        '[درصد تخفیف هدف]': (
            _format_percent_label(fixed_discount_notice.get('discount_percent', 0))
            if fixed_discount_notice
            else next_discount_label
        ),
        '[انعام]': format_toman(resolved_tip),
        '[تخفیف مجموعه]': format_toman(resolved_facility),
        '[تخفیف امتیاز مشتری]': format_toman(resolved_loyalty),
        '[تخفیف دستی]': format_toman(resolved_manual),
        '[جمع تخفیف]': format_toman(resolved_discount),
        '[مالیات]': format_toman(resolved_tax),
        '[مبلغ نهایی]': format_toman(resolved_final),
    }


def build_vehicle_assignment_sms_context(vehicle, *, assigned_at=None, visit_count=None, settings_obj=None):
    return build_vehicle_sms_token_context(
        vehicle,
        assigned_at=assigned_at,
        visit_count=visit_count,
        settings_obj=settings_obj,
    )


def build_vehicle_assignment_sms(settings_obj, vehicle, *, assigned_at=None, visit_count=None):
    vehicle = refresh_vehicle_for_sms(vehicle)
    context = build_vehicle_assignment_sms_context(
        vehicle,
        assigned_at=assigned_at,
        visit_count=visit_count,
        settings_obj=settings_obj,
    )
    intro_template = str(
        getattr(settings_obj, 'sms_vehicle_assigned_template', '')
        or DEFAULT_SMS_VEHICLE_ASSIGNED_TEMPLATE
    ).strip()
    invoice_template = str(
        getattr(settings_obj, 'sms_vehicle_assigned_invoice_template', '')
        or DEFAULT_SMS_VEHICLE_ASSIGNED_INVOICE_TEMPLATE
    ).strip()
    template = normalize_vehicle_assignment_sms_template('\n\n'.join(part for part in [intro_template, invoice_template] if part))
    return render_template_tokens(template, context), context


def build_vehicle_assignment_sms_messages(settings_obj, vehicle, *, assigned_at=None, visit_count=None):
    vehicle = refresh_vehicle_for_sms(vehicle)
    context = build_vehicle_assignment_sms_context(
        vehicle,
        assigned_at=assigned_at,
        visit_count=visit_count,
        settings_obj=settings_obj,
    )
    assigned_enabled = getattr(settings_obj, 'sms_vehicle_assigned_enabled', True) if settings_obj is not None else True
    assigned_template = str(
        getattr(settings_obj, 'sms_vehicle_assigned_template', '')
        or DEFAULT_SMS_VEHICLE_ASSIGNED_TEMPLATE
    ).strip()
    invoice_template = str(
        getattr(settings_obj, 'sms_vehicle_assigned_invoice_template', '')
    ).strip()
    messages = []
    if assigned_enabled:
        template_parts = [assigned_template]
        if invoice_template and '[خلاصه خدمات]' not in assigned_template:
            template_parts.append(invoice_template)
        normalized_template = normalize_vehicle_assignment_sms_template('\n'.join(template_parts)).strip()
        if '[شماره پذیرش]' not in normalized_template:
            lines = normalized_template.splitlines()
            lines.insert(1 if lines else 0, 'شماره پذیرش: [شماره پذیرش]')
            normalized_template = '\n'.join(lines)
        assignment_text = render_template_tokens(normalized_template, context).strip()
        if assignment_text:
            messages.append({
                'text': assignment_text,
                'context': context,
                'template_code': 'vehicle_assigned',
                'reference_type': 'vehicle_assigned_sms',
                'description': 'ارسال پیامک پذیرش خودرو',
            })
    return messages


def prepare_released_discount_template(template, *, mode='step', has_fixed_notice=False):
    lines = []
    for line in str(template or '').split('\n'):
        has_token = '[درصد تخفیف مراجعه بعد]' in line or '[درصد تخفیف سفارش بعد]' in line
        if not has_token:
            lines.append(line)
            continue
        if mode == 'fixed':
            if not has_fixed_notice:
                continue
            lines.append('[درصد تخفیف مراجعه بعد]')
            continue
        lines.append(line)
    return '\n'.join(lines)


def build_vehicle_released_sms(
    settings_obj,
    vehicle,
    *,
    released_at=None,
    customer_score=0,
    next_discount_percent=0,
    final_total=0,
    discount_total=0,
    visit_count=0,
    tip_amount=0,
    facility_discount_total=0,
    loyalty_discount_total=0,
    manual_discount_total=0,
    tax_total=0,
):
    vehicle = refresh_vehicle_for_sms(vehicle)
    released_at = released_at or getattr(vehicle, 'released_at', None) or getattr(vehicle, 'updated_at', None) or timezone.now()
    mode = loyalty_discount_mode(settings_obj)
    fixed_discount_notice = next_fixed_discount_notice(settings_obj, visit_count) if mode == 'fixed' else None
    context = build_vehicle_sms_token_context(
        vehicle,
        released_at=released_at,
        visit_count=visit_count,
        customer_score=customer_score,
        next_discount_percent=next_discount_percent,
        final_total=final_total,
        discount_total=discount_total,
        tip_amount=tip_amount,
        facility_discount_total=facility_discount_total,
        loyalty_discount_total=loyalty_discount_total,
        manual_discount_total=manual_discount_total,
        tax_total=tax_total,
        settings_obj=settings_obj,
    )
    template = prepare_released_discount_template(
        normalize_vehicle_released_sms_template(
            getattr(settings_obj, 'sms_vehicle_released_template', '')
            or DEFAULT_SMS_VEHICLE_RELEASED_TEMPLATE
        ),
        mode=mode,
        has_fixed_notice=bool(fixed_discount_notice and fixed_discount_notice.get('text')),
    )
    return render_template_tokens(template, context), context


def sms_wallet_balance(tenant):
    from apps.payments.models import Wallet

    return (
        Wallet.objects.filter(
            tenant=tenant,
            wallet_type=Wallet.WalletType.SMS,
            is_active=True,
        ).aggregate(total=Coalesce(Sum('balance'), Value(Decimal('0'))))['total']
        or Decimal('0')
    )


def debit_sms_wallets(tenant, amount, *, description, reference_type, created_by=None):
    from apps.payments.models import CashflowTransaction, Wallet
    from apps.notifications.models import NotificationLog

    remaining = Decimal(str(amount or 0))
    with transaction.atomic():
        wallets = list(
            Wallet.objects.select_for_update()
            .filter(tenant=tenant, wallet_type=Wallet.WalletType.SMS, is_active=True)
            .order_by('id')
        )
        for wallet in wallets:
            if remaining <= 0:
                break
            current_balance = Decimal(str(wallet.balance or 0))
            if current_balance <= 0:
                continue
            debit = min(current_balance, remaining)
            wallet.balance = current_balance - debit
            wallet.save(update_fields=['balance', 'updated_at'])
            CashflowTransaction.objects.create(
                tenant=tenant,
                wallet=wallet,
                direction=CashflowTransaction.Direction.OUT,
                amount=debit,
                description=description,
                reference_type=reference_type,
                created_by=created_by if getattr(created_by, 'is_authenticated', False) else None,
            )
            remaining -= debit
    return remaining <= 0


def provider_message_text(provider_data, fallback='ارسال پیامک توسط سرویس تایید نشد.'):
    if isinstance(provider_data, dict):
        message = provider_data.get('message') or provider_data.get('messages')
        if isinstance(message, list):
            return ' | '.join(str(item) for item in message if item)
        if isinstance(message, dict):
            return json.dumps(message, ensure_ascii=False)
        if message:
            try:
                return bytes(str(message), 'utf-8').decode('unicode_escape')
            except Exception:
                return str(message)
    if provider_data:
        return str(provider_data)
    return fallback


def sms_provider_config():
    return {
        'api_key': str(getattr(settings, 'IRANPAYAMAK_API_KEY', '') or '').strip(),
        'line_number': str(getattr(settings, 'IRANPAYAMAK_LINE_NUMBER', '') or '').strip(),
        'base_url': str(
            getattr(settings, 'IRANPAYAMAK_BASE_URL', 'https://api.iranpayamak.com')
            or 'https://api.iranpayamak.com'
        ).rstrip('/'),
    }


def send_provider_sms(tenant, text, recipients, *, provider_config=None):
    config = provider_config or sms_provider_config()
    api_key = str(config.get('api_key', '') or '').strip()
    line_number = str(config.get('line_number', '') or '').strip()
    base_url = str(config.get('base_url', 'https://api.iranpayamak.com') or 'https://api.iranpayamak.com').rstrip('/')
    if not api_key or not line_number:
        message = 'تنظیمات سرویس پیامک کامل نیست.'
        return {'ok': False, 'message': message, 'provider_status': 0, 'provider_data': {}, 'raw_body': message, 'payload': {}}

    payload = {
        'text': text,
        'line_number': line_number,
        'recipients': recipients,
        'number_format': 'english',
        'schedule': None,
    }
    req = urllib_request.Request(
        url=f'{base_url}/ws/v1/sms/simple',
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Api-Key': api_key,
        },
        method='POST',
    )
    try:
        with urllib_request.urlopen(req, timeout=15) as response:
            raw_body = response.read().decode('utf-8')
            response_status = response.status
    except urllib_error.HTTPError as exc:
        raw_body = exc.read().decode('utf-8', errors='replace')
        try:
            provider_data = json.loads(raw_body or '{}') if raw_body else {}
        except json.JSONDecodeError:
            provider_data = {'message': raw_body}
        return {
            'ok': False,
            'message': provider_message_text(provider_data, fallback='سرویس پیامک درخواست را نپذیرفت.'),
            'provider_status': exc.code,
            'provider_data': provider_data,
            'raw_body': raw_body,
            'payload': payload,
        }
    except urllib_error.URLError as exc:
        provider_response = str(getattr(exc, 'reason', exc))
        return {
            'ok': False,
            'message': 'ارتباط با سرویس پیامک برقرار نشد.',
            'provider_status': 0,
            'provider_data': {'message': provider_response},
            'raw_body': provider_response,
            'payload': payload,
        }

    try:
        provider_data = json.loads(raw_body or '{}') if raw_body else {}
    except json.JSONDecodeError:
        provider_data = {'status': 'error', 'message': raw_body}
    if response_status not in {200, 201} or provider_data.get('status') != 'success':
        return {
            'ok': False,
            'message': provider_message_text(provider_data),
            'provider_status': response_status,
            'provider_data': provider_data,
            'raw_body': raw_body,
            'payload': payload,
        }

    data = provider_data.get('data')
    provider_id = str(data.get('id') or '') if isinstance(data, dict) else str(data or '')
    provider_delivery_status = str(data.get('status') or '') if isinstance(data, dict) else ''
    return {
        'ok': True,
        'message': 'پیامک با موفقیت در صف ارسال قرار گرفت.',
        'provider_status': response_status,
        'provider_data': provider_data,
        'provider_id': provider_id,
        'provider_delivery_status': provider_delivery_status,
        'raw_body': raw_body,
        'payload': payload,
    }

def send_provider_pattern_sms(
    tenant,
    recipient,
    pattern_code,
    attributes,
    *,
    provider_config=None,
):
    config = provider_config or sms_provider_config()

    api_key = str(config.get('api_key', '') or '').strip()
    line_number = str(config.get('line_number', '') or '').strip()
    base_url = str(
        config.get('base_url', 'https://api.iranpayamak.com')
        or 'https://api.iranpayamak.com'
    ).rstrip('/')

    if not api_key or not line_number:
        return {
            'ok': False,
            'message': 'تنظیمات سرویس پیامک کامل نیست.',
            'provider_status': 0,
            'provider_data': {},
            'raw_body': '',
            'payload': {},
        }

    payload = {
        'code': pattern_code,
        'attributes': attributes,
        'recipient': recipient,
        'line_number': line_number,
        'number_format': 'english',

    }

    req = urllib_request.Request(
        url=f'{base_url}/ws/v1/sms/pattern',
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Api-Key': api_key,
        },
        method='POST',
    )

    try:
        with urllib_request.urlopen(req, timeout=15) as response:
            raw_body = response.read().decode('utf-8')
            response_status = response.status

    except urllib_error.HTTPError as exc:
        raw_body = exc.read().decode('utf-8', errors='replace')

        try:
            provider_data = json.loads(raw_body or '{}')
        except json.JSONDecodeError:
            provider_data = {'message': raw_body}

        return {
            'ok': False,
            'message': provider_message_text(
                provider_data,
                fallback='سرویس پیامک درخواست را نپذیرفت.',
            ),
            'provider_status': exc.code,
            'provider_data': provider_data,
            'raw_body': raw_body,
            'payload': payload,
        }

    except urllib_error.URLError as exc:
        message = str(getattr(exc, 'reason', exc))

        return {
            'ok': False,
            'message': 'ارتباط با سرویس پیامک برقرار نشد.',
            'provider_status': 0,
            'provider_data': {'message': message},
            'raw_body': message,
            'payload': payload,
        }

    try:
        provider_data = json.loads(raw_body or '{}')
    except json.JSONDecodeError:
        provider_data = {
            'status': 'error',
            'message': raw_body,
        }

    if response_status not in {200, 201} or provider_data.get('status') != 'success':
        return {
            'ok': False,
            'message': provider_message_text(provider_data),
            'provider_status': response_status,
            'provider_data': provider_data,
            'raw_body': raw_body,
            'payload': payload,
        }

    data = provider_data.get('data')

    provider_id = (
        str(data.get('id') or '')
        if isinstance(data, dict)
        else str(data or '')
    )

    return {
        'ok': True,
        'message': 'پیامک پترن با موفقیت ارسال شد.',
        'provider_status': response_status,
        'provider_data': provider_data,
        'provider_id': provider_id,
        'raw_body': raw_body,
        'payload': payload,
    }

def _send_vehicle_event_sms_sync(event_code, tenant, vehicle, *, created_by=None, extra_context=None):
    from apps.notifications.models import NotificationLog

    if (
        event_code in {'vehicle_assigned', 'vehicle_released'}
        and getattr(vehicle, 'sms_notifications_enabled', True) is False
    ):
        return {
            'ok': False,
            'skipped': True,
            'reason': 'vehicle_sms_disabled',
        }

    extra_context = extra_context or {}
    phone = normalize_phone(getattr(vehicle, 'driver_phone', ''))
    if not is_valid_iran_mobile(phone):
        NotificationLog.objects.create(
            tenant=tenant,
            vehicle_entry=vehicle,
            channel=NotificationLog.Channel.SMS,
            recipient=phone or '',
            template_code=event_code,
            payload=make_json_safe({
                'event_code': event_code,
                'reason': 'invalid_mobile',
                'driver_phone': getattr(vehicle, 'driver_phone', ''),
            }),
            status=NotificationLog.Status.FAILED,
            provider_response='شماره موبایل خودرو معتبر نیست و باید با 09 شروع شود.',
            created_by=created_by if getattr(created_by, 'is_authenticated', False) else None,
        )
        return {'ok': False, 'reason': 'invalid_phone'}

    settings_obj = GeneralSettings.objects.filter(tenant=tenant).order_by('id').first()
    if (
        event_code in {'vehicle_assigned', 'vehicle_released'}
        and settings_obj is not None
        and getattr(settings_obj, 'sms_vehicle_auto_send_enabled', True) is False
    ):
        return {
            'ok': False,
            'skipped': True,
            'reason': 'vehicle_auto_sms_disabled',
        }

    if event_code == 'vehicle_assigned':
        message_items = build_vehicle_assignment_sms_messages(
            settings_obj,
            vehicle,
            assigned_at=extra_context.get('assigned_at'),
            visit_count=extra_context.get('visit_count'),
        )
    elif event_code == 'vehicle_released':
        if settings_obj is not None and getattr(settings_obj, 'sms_vehicle_released_enabled', True) is False:
            return {
                'ok': False,
                'skipped': True,
                'reason': 'vehicle_released_sms_disabled',
            }
        text, context = build_vehicle_released_sms(
            settings_obj,
            vehicle,
            released_at=extra_context.get('released_at'),
            customer_score=extra_context.get('customer_score', 0),
            next_discount_percent=extra_context.get('next_discount_percent', 0),
            final_total=extra_context.get('final_total', 0),
            discount_total=extra_context.get('discount_total', 0),
            visit_count=extra_context.get('visit_count', 0),
            tip_amount=extra_context.get('tip_amount', 0),
            facility_discount_total=extra_context.get('facility_discount_total', 0),
            loyalty_discount_total=extra_context.get('loyalty_discount_total', 0),
            manual_discount_total=extra_context.get('manual_discount_total', 0),
            tax_total=extra_context.get('tax_total', 0),
        )
        message_items = [{
            'text': text,
            'context': context,
            'template_code': event_code,
            'reference_type': 'vehicle_released_sms',
            'description': 'ارسال پیامک ترخیص خودرو',
        }]
    else:
        return {'ok': False, 'reason': 'unsupported_event'}

    message_items = [
        {**item, 'text': str(item.get('text') or '').strip()}
        for item in message_items
        if str(item.get('text') or '').strip()
    ]
    if not message_items:
        return {'ok': False, 'reason': 'empty_template'}

    try:
        from apps.auth.sample_tenant import assert_sample_sms_capacity, maybe_raise_sample_monthly_sms_alert

        assert_sample_sms_capacity(tenant, extra=len(message_items))
    except ValueError as exc:
        NotificationLog.objects.create(
            tenant=tenant,
            vehicle_entry=vehicle,
            channel=NotificationLog.Channel.SMS,
            recipient=phone,
            template_code=event_code,
            payload=make_json_safe({
                'event_code': event_code,
                'reason': 'sample_daily_sms_cap',
                'detail': str(exc),
            }),
            status=NotificationLog.Status.FAILED,
            provider_response=str(exc),
            created_by=created_by if getattr(created_by, 'is_authenticated', False) else None,
        )
        return {'ok': False, 'reason': 'sample_daily_sms_cap', 'detail': str(exc)}

    sms_price = sms_price_per_segment()
    estimated_cost = sum((sms_cost_for_text(item['text']) for item in message_items), Decimal('0'))
    balance = sms_wallet_balance(tenant)

    payload = make_json_safe({
        'event_code': event_code,
        'customer_name': customer_display_name(getattr(vehicle, 'driver_name', '')),
        'plate_number': getattr(vehicle, 'plate_number', ''),
        'estimated_cost': float(estimated_cost),
        **extra_context,
    })

    if balance < estimated_cost:
        NotificationLog.objects.create(
            tenant=tenant,
            vehicle_entry=vehicle,
            channel=NotificationLog.Channel.SMS,
            recipient=phone,
            template_code=event_code,
            payload=payload,
            status=NotificationLog.Status.FAILED,
            provider_response='موجودی کیف پول پیامک کافی نیست.',
            created_by=created_by if getattr(created_by, 'is_authenticated', False) else None,
        )
        return {'ok': False, 'reason': 'insufficient_balance'}

    sent_count = 0
    for item in message_items:
        item_cost = sms_cost_for_text(item['text'])
        item_payload = make_json_safe({
            **payload,
            'text': item['text'],
            'character_count': len(sms_billable_text(item['text'])),
            'estimated_cost': float(item_cost),
            'segments': sms_segments_for_text(item['text']),
            'price_per_segment': float(sms_price),
            **{key.strip('[]'): value for key, value in item.get('context', {}).items()},
        })
        provider_result = send_provider_sms(tenant, item['text'], [phone])
        item_payload['provider_request'] = make_json_safe(provider_result.get('payload', {}))
        if not provider_result.get('ok'):
            NotificationLog.objects.create(
                tenant=tenant,
                vehicle_entry=vehicle,
                channel=NotificationLog.Channel.SMS,
                recipient=phone,
                template_code=item.get('template_code') or event_code,
                payload=item_payload,
                status=NotificationLog.Status.FAILED,
                provider_response=provider_result.get('raw_body') or provider_result.get('message', ''),
                created_by=created_by if getattr(created_by, 'is_authenticated', False) else None,
            )
            return {'ok': False, 'reason': 'provider_failed', 'sent_count': sent_count}

        debit_sms_wallets(
            tenant,
            item_cost,
            description=item.get('description') or 'ارسال پیامک خودرو',
            reference_type=item.get('reference_type') or 'vehicle_sms',
            created_by=created_by,
        )
        NotificationLog.objects.create(
            tenant=tenant,
            vehicle_entry=vehicle,
            channel=NotificationLog.Channel.SMS,
            recipient=phone,
            template_code=item.get('template_code') or event_code,
            payload=item_payload,
            status=NotificationLog.Status.SENT,
            sent_at=timezone.now(),
            provider_message_id=provider_result.get('provider_id', ''),
            provider_response=provider_result.get('raw_body') or provider_result.get('message', ''),
            created_by=created_by if getattr(created_by, 'is_authenticated', False) else None,
        )
        sent_count += 1
    if sent_count:
        maybe_raise_sample_monthly_sms_alert()
    return {'ok': True, 'sent_count': sent_count}


def _run_vehicle_event_sms_job(event_code, vehicle_id, tenant_id, created_by_id, extra_context):
    from django.contrib.auth import get_user_model

    from apps.auth.models import CarWash
    from apps.vehicles.models import VehicleEntry

    close_old_connections()
    try:
        vehicle = (
            VehicleEntry.objects.select_related('tenant', 'job', 'customer')
            .prefetch_related('job__service_lines__service', 'job__product_lines__product')
            .filter(id=vehicle_id)
            .first()
        )
        if not vehicle:
            return
        tenant = vehicle.tenant
        if tenant_id and (not tenant or int(tenant.id) != int(tenant_id)):
            tenant = CarWash.objects.filter(id=tenant_id).first() or tenant
        created_by = None
        if created_by_id:
            created_by = get_user_model().objects.filter(id=created_by_id).first()
        _send_vehicle_event_sms_sync(
            event_code,
            tenant,
            vehicle,
            created_by=created_by,
            extra_context=extra_context or {},
        )
    except Exception:
        logger.exception(
            'Background vehicle SMS failed event=%s vehicle_id=%s',
            event_code,
            vehicle_id,
        )
    finally:
        close_old_connections()


def send_vehicle_event_sms(event_code, tenant, vehicle, *, created_by=None, extra_context=None, background=None):
    """Send assignment/release SMS. By default queues after DB commit so UI isn't blocked."""
    if background is None:
        background = bool(getattr(settings, 'SMS_SEND_IN_BACKGROUND', True))

    if not background:
        return _send_vehicle_event_sms_sync(
            event_code,
            tenant,
            vehicle,
            created_by=created_by,
            extra_context=extra_context,
        )

    vehicle_id = getattr(vehicle, 'id', None) or getattr(vehicle, 'pk', None)
    if not vehicle_id:
        return _send_vehicle_event_sms_sync(
            event_code,
            tenant,
            vehicle,
            created_by=created_by,
            extra_context=extra_context,
        )

    tenant_id = getattr(tenant, 'id', None) or getattr(vehicle, 'tenant_id', None)
    created_by_id = None
    if created_by and getattr(created_by, 'is_authenticated', False):
        created_by_id = getattr(created_by, 'id', None)
    job_extra = dict(extra_context or {})

    def enqueue():
        worker = threading.Thread(
            target=_run_vehicle_event_sms_job,
            args=(event_code, int(vehicle_id), tenant_id, created_by_id, job_extra),
            name=f'vehicle-sms-{event_code}-{vehicle_id}',
            daemon=True,
        )
        worker.start()

    transaction.on_commit(enqueue)
    return {'ok': True, 'queued': True}


def customer_key_for(customer_id=None, phone='', name=''):
    if customer_id:
        return f'customer:{int(customer_id)}'
    normalized_phone = normalize_phone(phone)
    normalized_name = '-'.join(str(name or '').strip().split()) or 'anonymous'
    return f'fallback:{normalized_phone or "no-phone"}:{normalized_name}'


def serialize_decimal(value):
    if value is None:
        return 0
    return float(Decimal(str(value)))


def _attach_customer_plate(record, *, plate_number='', plate_left='', plate_letter='', plate_mid='', plate_right='', plate_type=None):
    plate = str(plate_number or '').strip()
    if not plate or plate == '1111':
        return
    if plate not in {entry['plate_number'] for entry in record['plates']}:
        record['plates'].append({
            'plate_number': plate,
            'plate_left': str(plate_left or '').strip(),
            'plate_letter': str(plate_letter or '').strip(),
            'plate_mid': str(plate_mid or '').strip(),
            'plate_right': str(plate_right or '').strip(),
            'plate_type': str(plate_type or VehicleEntry.PlateType.CAR).strip() or VehicleEntry.PlateType.CAR,
        })
    if record['plates'] and not record['primary_plate']:
        record['primary_plate'] = record['plates'][0]['plate_number']
        record['primary_plate_left'] = record['plates'][0]['plate_left']
        record['primary_plate_letter'] = record['plates'][0]['plate_letter']
        record['primary_plate_mid'] = record['plates'][0]['plate_mid']
        record['primary_plate_right'] = record['plates'][0]['plate_right']
        record['primary_plate_type'] = record['plates'][0]['plate_type']


def ensure_default_sms_templates(tenant, user=None):
    from .models import SmsTemplate

    existing_codes = set(
        SmsTemplate.objects.filter(tenant=tenant).values_list('code', flat=True)
    )
    missing = [item for item in DEFAULT_SMS_TEMPLATES if item['code'] not in existing_codes]
    if not missing:
        return

    SmsTemplate.objects.bulk_create([
        SmsTemplate(
            tenant=tenant,
            code=item['code'],
            title=item['title'],
            body=item['body'],
            display_order=item['display_order'],
            is_active=True,
            created_by=user if getattr(user, 'is_authenticated', False) else None,
        )
        for item in missing
    ])


def build_customer_summaries(tenant):
    from .models import ImportedCustomer

    rows = (
        VehicleEntry.objects.select_related('customer', 'job')
        .filter(tenant=tenant)
        .exclude(status=VehicleEntry.Status.CANCELLED)
        .order_by('-check_in_at')
    )

    customer_map = {}
    for item in rows:
        key = customer_key_for(
            customer_id=getattr(item.customer, 'id', None),
            phone=item.driver_phone,
            name=item.driver_name,
        )
        event_date = item.released_at or item.updated_at or item.check_in_at or item.created_at
        record = customer_map.get(key)
        if record is None:
            record = {
                'key': key,
                'customer_id': getattr(item.customer, 'id', None),
                'name': (getattr(item.customer, 'full_name', '') or item.driver_name or 'مشتری بدون نام').strip() or 'مشتری بدون نام',
                'phone': normalize_phone(item.driver_phone),
                'carwash_name': getattr(tenant, 'name', '') or 'کارواش',
                'orders_count': 0,
                'total_spent': 0.0,
                'score': float(getattr(item.customer, 'yearly_score', 0) or 0),
                'last_order_at': event_date,
                'first_order_at': event_date,
                'plates': [],
                'primary_plate': '',
                'primary_plate_left': '',
                'primary_plate_letter': '',
                'primary_plate_mid': '',
                'primary_plate_right': '',
                'primary_plate_type': VehicleEntry.PlateType.CAR,
            }
            customer_map[key] = record

        record['orders_count'] += 1
        record['total_spent'] += serialize_decimal(
            getattr(getattr(item, 'job', None), 'final_total', 0)
            or getattr(getattr(item, 'job', None), 'services_total', 0)
            or 0
        )
        record['score'] = max(
            float(record['score'] or 0),
            float(getattr(item.customer, 'yearly_score', 0) or 0),
        )
        if not record['last_order_at'] or (event_date and event_date > record['last_order_at']):
            record['last_order_at'] = event_date
        if not record['first_order_at'] or (event_date and event_date < record['first_order_at']):
            record['first_order_at'] = event_date

        plate = str(item.plate_number or '').strip()
        if plate and plate != '1111' and plate not in {entry['plate_number'] for entry in record['plates']}:
            record['plates'].append({
                'plate_number': plate,
                'plate_left': str(item.plate_left or '').strip(),
                'plate_letter': str(item.plate_letter or '').strip(),
                'plate_mid': str(item.plate_mid or '').strip(),
                'plate_right': str(item.plate_right or '').strip(),
                'plate_type': str(item.plate_type or VehicleEntry.PlateType.CAR).strip() or VehicleEntry.PlateType.CAR,
            })
        if record['plates'] and not record['primary_plate']:
            record['primary_plate'] = record['plates'][0]['plate_number']
            record['primary_plate_left'] = record['plates'][0]['plate_left']
            record['primary_plate_letter'] = record['plates'][0]['plate_letter']
            record['primary_plate_mid'] = record['plates'][0]['plate_mid']
            record['primary_plate_right'] = record['plates'][0]['plate_right']
            record['primary_plate_type'] = record['plates'][0]['plate_type']

    for item in ImportedCustomer.objects.filter(tenant=tenant).order_by('-updated_at', '-id'):
        phone = normalize_phone(item.phone)
        key = next(
            (
                existing_key
                for existing_key, existing_record in customer_map.items()
                if phone and existing_record.get('phone') == phone
            ),
            customer_key_for(phone=phone, name=item.full_name),
        )
        event_date = item.updated_at or item.created_at
        record = customer_map.get(key)
        if record is None:
            record = {
                'key': key,
                'customer_id': None,
                'name': (item.full_name or 'مشتری بدون نام').strip() or 'مشتری بدون نام',
                'phone': phone,
                'carwash_name': getattr(tenant, 'name', '') or 'کارواش',
                'orders_count': 0,
                'total_spent': 0.0,
                'score': 0.0,
                'last_order_at': event_date,
                'first_order_at': event_date,
                'plates': [],
                'primary_plate': '',
                'primary_plate_left': '',
                'primary_plate_letter': '',
                'primary_plate_mid': '',
                'primary_plate_right': '',
                'primary_plate_type': VehicleEntry.PlateType.CAR,
                'source': 'imported',
            }
            customer_map[key] = record
        elif item.full_name and (not record.get('name') or record.get('name') == 'مشتری بدون نام'):
            record['name'] = item.full_name
        if event_date and (not record['last_order_at'] or event_date > record['last_order_at']):
            record['last_order_at'] = event_date
        _attach_customer_plate(record, plate_number=item.plate_number)

    result = list(customer_map.values())
    for item in result:
        item['average_ticket'] = round((item['total_spent'] / item['orders_count']) if item['orders_count'] else 0, 2)
    result.sort(key=lambda item: item['last_order_at'] or '', reverse=True)
    return result


def customer_matches_rules(customer, rules):
    if not rules:
        return True
    if rules.get('carwash') and customer.get('carwash_name') != rules.get('carwash'):
        return False
    if float(customer.get('orders_count') or 0) < float(rules.get('minOrders') or 0):
        return False
    if float(customer.get('total_spent') or 0) < float(rules.get('minSpent') or 0):
        return False
    if float(customer.get('score') or 0) < float(rules.get('minScore') or 0):
        return False
    return True


def resolve_group_members(group, customers):
    if not group:
        return []
    if group.mode == group.Mode.SMART:
        return [customer for customer in customers if customer_matches_rules(customer, group.rules)]
    member_keys = set(group.member_keys or [])
    return [customer for customer in customers if customer.get('key') in member_keys]


def render_sms_text(template_text, customer, tenant_name=''):
    message = str(template_text or '').strip()
    total_spent = int(round(float(customer.get('total_spent') or 0)))
    replacements = {
        '[نام مشتری]': customer.get('name') or 'مشتری',
        '[نام کارواش]': customer.get('carwash_name') or tenant_name or 'کارواش',
        '[تعداد سفارش]': str(int(customer.get('orders_count') or 0)),
        '[جمع خرید]': f'{total_spent:,}'.replace(',', '،'),
        '[امتیاز]': str(customer.get('score') or 0),
        '[آخرین مراجعه]': str(customer.get('last_order_at') or ''),
        '[پلاک]': customer.get('primary_plate') or '',
    }
    for token, value in replacements.items():
        message = message.replace(token, str(value))
    return message


def group_sms_batches(recipients, template_text, tenant_name):
    grouped = defaultdict(list)
    rendered = []
    for recipient in recipients:
        normalized = dict(recipient)
        normalized['phone'] = normalize_phone(recipient.get('phone'))
        rendered_text = render_sms_text(template_text, normalized, tenant_name=tenant_name)
        normalized['rendered_text'] = rendered_text
        grouped[rendered_text].append(normalized)
        rendered.append(normalized)
    return grouped, rendered


def extract_log_metadata(log):
    payload = log.payload or {}
    mapped_status = 'success' if log.status == 'sent' else log.status
    template_code = str(log.template_code or payload.get('template_code') or '').strip()
    event_code = str(payload.get('event_code') or template_code or '').strip()
    if event_code in {'vehicle_assigned', 'vehicle_assigned_sms'}:
        event_label = 'پیامک پذیرش'
    elif event_code in {'vehicle_released', 'vehicle_released_sms'}:
        event_label = 'پیامک ترخیص'
    elif event_code:
        event_label = event_code
    else:
        event_label = payload.get('target_label', '') or 'پیامک'
    return {
        'id': log.id,
        'status': mapped_status,
        'recipient_name': payload.get('recipient_name') or payload.get('customer', {}).get('name') or '',
        'phone': log.recipient,
        'target_label': payload.get('target_label', '') or event_label,
        'event_code': event_code,
        'event_label': event_label,
        'template_code': template_code,
        'message': payload.get('rendered_text') or payload.get('text') or '',
        'note': payload.get('note', ''),
        'created_at': log.created_at,
        'provider_message_id': log.provider_message_id,
        'provider_response': log.provider_response,
        'campaign_id': payload.get('campaign_id', ''),
    }
