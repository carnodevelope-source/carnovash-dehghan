import json
import math
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from urllib import error as urllib_error
from urllib import request as urllib_request

from django.conf import settings
from django.db import transaction
from django.db.models import Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.services.models import (
    DEFAULT_SMS_VEHICLE_ASSIGNED_INVOICE_TEMPLATE,
    DEFAULT_SMS_VEHICLE_ASSIGNED_TEMPLATE,
    DEFAULT_SMS_VEHICLE_RELEASED_TEMPLATE,
    GeneralSettings,
    normalize_vehicle_released_sms_template,
)
from apps.vehicles.models import VehicleEntry


PERSIAN_DIGITS = '۰۱۲۳۴۵۶۷۸۹'
ARABIC_DIGITS = '٠١٢٣٤٥٦٧٨٩'

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
        return 'آقا'
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


def refresh_vehicle_for_sms(vehicle):
    vehicle_id = getattr(vehicle, 'pk', None) or getattr(vehicle, 'id', None)
    if not vehicle_id:
        return vehicle
    return (
        VehicleEntry.objects.select_related('tenant', 'job')
        .prefetch_related('job__service_lines__service')
        .filter(pk=vehicle_id)
        .first()
        or vehicle
    )


def assignment_invoice_total(job):
    if not job:
        return 0
    final_total = Decimal(str(getattr(job, 'final_total', 0) or 0))
    if final_total > 0:
        return final_total
    services_total = Decimal(str(getattr(job, 'services_total', 0) or 0))
    products_total = Decimal(str(getattr(job, 'products_total', 0) or 0))
    if services_total > 0 or products_total > 0:
        return services_total + products_total
    line_total = Decimal('0')
    for line in iter_service_lines(job):
        line_total += Decimal(str(getattr(line, 'line_total', 0) or 0))
    return line_total


def build_services_sms_summary(job):
    lines = []
    for line in iter_service_lines(job):
        title = str(
            getattr(line, 'custom_service_name', '')
            or getattr(getattr(line, 'service', None), 'name', '')
            or getattr(line, 'service_name', '')
            or 'خدمت'
        ).strip()
        line_total = getattr(line, 'line_total', 0)
        lines.append(f'{title} ---- {format_toman(line_total)}')
    return '\n'.join(lines) if lines else 'خدمات ثبت شده است ---- مبلغ هنگام نهایی‌سازی اعلام می‌شود'


def render_template_tokens(template_text, context):
    message = str(template_text or '').strip()
    for token, value in context.items():
        message = message.replace(token, str(value))
    return message


def build_vehicle_assignment_sms(settings_obj, vehicle, *, assigned_at=None):
    vehicle = refresh_vehicle_for_sms(vehicle)
    assigned_at = assigned_at or getattr(vehicle, 'ready_at', None) or getattr(vehicle, 'updated_at', None) or timezone.now()
    job = getattr(vehicle, 'job', None)
    plate_label = str(getattr(vehicle, 'plate_number', '') or '').strip() or 'بدون پلاک'
    driver_gender = getattr(vehicle, 'driver_gender', '') or getattr(getattr(vehicle, 'customer', None), 'gender', '')
    context = {
        '[نام مشتری]': customer_display_name_with_title(getattr(vehicle, 'driver_name', ''), driver_gender) or 'مشتری',
        '[خطاب مشتری]': customer_greeting(getattr(vehicle, 'driver_name', ''), driver_gender),
        '[جنسیت مشتری]': customer_title(driver_gender),
        '[نام کارواش]': getattr(getattr(vehicle, 'tenant', None), 'name', '') or 'کارواش',
        '[پلاک]': plate_label,
        '[ساعت تخصیص]': format_local_time(assigned_at),
        '[تاریخ تخصیص]': format_jalali_date(assigned_at),
        '[خلاصه خدمات]': build_services_sms_summary(job),
        '[جمع کل]': format_toman(assignment_invoice_total(job)),
    }
    intro_template = str(
        getattr(settings_obj, 'sms_vehicle_assigned_template', '')
        or DEFAULT_SMS_VEHICLE_ASSIGNED_TEMPLATE
    ).strip()
    invoice_template = str(getattr(settings_obj, 'sms_vehicle_assigned_invoice_template', '') or '').strip()
    template = '\n\n'.join(part for part in [intro_template, invoice_template] if part)
    return render_template_tokens(template, context), context


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
):
    released_at = released_at or getattr(vehicle, 'released_at', None) or getattr(vehicle, 'updated_at', None) or timezone.now()
    plate_label = str(getattr(vehicle, 'plate_number', '') or '').strip() or 'بدون پلاک'
    next_discount_label = f"{to_persian_digits(str(round(float(next_discount_percent or 0), 2)).replace('.0', ''))}٪"
    driver_gender = getattr(vehicle, 'driver_gender', '') or getattr(getattr(vehicle, 'customer', None), 'gender', '')
    context = {
        '[نام مشتری]': customer_display_name_with_title(getattr(vehicle, 'driver_name', ''), driver_gender) or 'مشتری',
        '[خطاب مشتری]': customer_greeting(getattr(vehicle, 'driver_name', ''), driver_gender),
        '[جنسیت مشتری]': customer_title(driver_gender),
        '[نام کارواش]': getattr(getattr(vehicle, 'tenant', None), 'name', '') or 'کارواش',
        '[پلاک]': plate_label,
        '[ساعت ترخیص]': format_local_time(released_at),
        '[تاریخ ترخیص]': format_jalali_date(released_at),
        '[امتیاز مشتری]': to_persian_digits(str(round(float(customer_score or 0), 1)).replace('.0', '')),
        '[درصد تخفیف سفارش بعد]': next_discount_label,
        '[درصد تخفیف امتیاز مشتری]': next_discount_label,
        '[تعداد مراجعات]': to_persian_digits(str(int(visit_count or 0))),
        '[انعام]': format_toman(tip_amount),
        '[جمع تخفیف]': format_toman(discount_total),
        '[تخفیف مجموعه]': format_toman(facility_discount_total),
        '[تخفیف امتیاز مشتری]': format_toman(loyalty_discount_total),
        '[تخفیف دستی]': format_toman(manual_discount_total),
        '[مبلغ نهایی]': format_toman(final_total),
    }
    template = normalize_vehicle_released_sms_template(
        getattr(settings_obj, 'sms_vehicle_released_template', '')
        or DEFAULT_SMS_VEHICLE_RELEASED_TEMPLATE
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


def send_vehicle_event_sms(event_code, tenant, vehicle, *, created_by=None, extra_context=None):
    from apps.notifications.models import NotificationLog

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
    if event_code == 'vehicle_assigned':
        text, context = build_vehicle_assignment_sms(
            settings_obj,
            vehicle,
            assigned_at=extra_context.get('assigned_at'),
        )
        reference_type = 'vehicle_assigned_sms'
        description = 'ارسال پیامک تخصیص خودرو'
    elif event_code == 'vehicle_released':
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
        )
        reference_type = 'vehicle_released_sms'
        description = 'ارسال پیامک ترخیص خودرو'
    else:
        return {'ok': False, 'reason': 'unsupported_event'}

    text = str(text or '').strip()
    if not text:
        return {'ok': False, 'reason': 'empty_template'}

    sms_price = Decimal(str(getattr(settings, 'SMS_PRICE_PER_SEGMENT', 500) or 500))
    segments = max(1, math.ceil(len(text) / 70))
    estimated_cost = sms_price * Decimal(segments)
    balance = sms_wallet_balance(tenant)

    payload = make_json_safe({
        'event_code': event_code,
        'text': text,
        'customer_name': customer_display_name(getattr(vehicle, 'driver_name', '')),
        'plate_number': getattr(vehicle, 'plate_number', ''),
        'estimated_cost': float(estimated_cost),
        **{key.strip('[]'): value for key, value in context.items()},
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

    provider_result = send_provider_sms(tenant, text, [phone])
    payload['provider_request'] = make_json_safe(provider_result.get('payload', {}))
    if not provider_result.get('ok'):
        NotificationLog.objects.create(
            tenant=tenant,
            vehicle_entry=vehicle,
            channel=NotificationLog.Channel.SMS,
            recipient=phone,
            template_code=event_code,
            payload=payload,
            status=NotificationLog.Status.FAILED,
            provider_response=provider_result.get('raw_body') or provider_result.get('message', ''),
            created_by=created_by if getattr(created_by, 'is_authenticated', False) else None,
        )
        return {'ok': False, 'reason': 'provider_failed'}

    debit_sms_wallets(
        tenant,
        estimated_cost,
        description=description,
        reference_type=reference_type,
        created_by=created_by,
    )
    NotificationLog.objects.create(
        tenant=tenant,
        vehicle_entry=vehicle,
        channel=NotificationLog.Channel.SMS,
        recipient=phone,
        template_code=event_code,
        payload=payload,
        status=NotificationLog.Status.SENT,
        sent_at=timezone.now(),
        provider_message_id=provider_result.get('provider_id', ''),
        provider_response=provider_result.get('raw_body') or provider_result.get('message', ''),
        created_by=created_by if getattr(created_by, 'is_authenticated', False) else None,
    )
    return {'ok': True}


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
    return {
        'id': log.id,
        'status': mapped_status,
        'recipient_name': payload.get('recipient_name') or payload.get('customer', {}).get('name') or '',
        'phone': log.recipient,
        'target_label': payload.get('target_label', ''),
        'message': payload.get('rendered_text') or payload.get('text') or '',
        'note': payload.get('note', ''),
        'created_at': log.created_at,
        'provider_message_id': log.provider_message_id,
        'provider_response': log.provider_response,
        'campaign_id': payload.get('campaign_id', ''),
    }
