from collections import defaultdict
from decimal import Decimal

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
                'name': (getattr(item.customer, 'full_name', '') or item.driver_name or 'مشتری بدون نام').strip() or 'مشتری بدون نام',
                'phone': normalize_phone(item.driver_phone),
                'carwash_name': getattr(tenant, 'name', '') or 'کارواش',
                'orders_count': 0,
                'total_spent': 0.0,
                'score': float(getattr(item.customer, 'yearly_score', 0) or 0),
                'last_order_at': event_date,
                'plates': [],
                'primary_plate': '',
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

        plate = str(item.plate_number or '').strip()
        if plate and plate != '1111' and plate not in record['plates']:
            record['plates'].append(plate)
        if record['plates'] and not record['primary_plate']:
            record['primary_plate'] = record['plates'][0]

    result = list(customer_map.values())
    result.sort(key=lambda item: item['last_order_at'] or '', reverse=True)
    return result


def customer_matches_rules(customer, rules):
    if not rules:
        return True
    if rules.get('carwash') and customer.get('carwash_name') != rules.get('carwash'):
        return False
    if float(customer.get('orders_count') or 0) < float(rules.get('minOrders') or 0):
        return False
    if float(customer.get('total_spent') or 0) < float(rules.get('minSpent') or 0) * 1000:
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
