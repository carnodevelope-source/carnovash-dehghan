from datetime import timedelta
import re
import time
from decimal import Decimal, ROUND_HALF_UP

from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

from apps.notifications.services import normalize_phone, send_provider_sms

from .models import SupportTicket, User


SUPPORT_TICKET_AUTO_CLOSE_AFTER_DAYS = 3
WALLET_CARD_DEPOSIT_TAX_PERCENT = Decimal('10')
_HQ_TICKET_SMS_CACHE_TTL_SECONDS = 60 * 60 * 24


def calculate_wallet_card_deposit_amounts(gross_amount):
    """Split a card-to-card deposit into gross, 10% tax, and net wallet credit."""
    gross = Decimal(str(gross_amount or 0))
    if gross <= 0:
        zero = Decimal('0')
        return zero, zero, zero
    tax = (gross * WALLET_CARD_DEPOSIT_TAX_PERCENT / Decimal('100')).quantize(
        Decimal('0.01'),
        rounding=ROUND_HALF_UP,
    )
    if tax >= gross:
        tax = max(Decimal('0'), gross - Decimal('0.01'))
    net = (gross - tax).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return gross, tax, net


_STALE_CLOSE_INTERVAL_SECONDS = 60
_last_stale_close_at = 0.0


def close_stale_support_tickets(*, now=None):
    global _last_stale_close_at
    current = now or timezone.now()
    if now is None:
        monotonic_now = time.monotonic()
        if monotonic_now - _last_stale_close_at < _STALE_CLOSE_INTERVAL_SECONDS:
            return 0
        _last_stale_close_at = monotonic_now
    cutoff = current - timedelta(days=SUPPORT_TICKET_AUTO_CLOSE_AFTER_DAYS)
    queryset = SupportTicket.objects.exclude(status=SupportTicket.Status.CLOSED).filter(
        Q(last_message_at__lte=cutoff)
        | Q(last_message_at__isnull=True, created_at__lte=cutoff)
    )
    return queryset.update(
        status=SupportTicket.Status.CLOSED,
        closed_at=current,
        updated_at=current,
    )


def is_wallet_card_payment_ticket(ticket):
    text = f'{getattr(ticket, "subject", "")}\n{getattr(ticket, "message", "")}'.lower()
    return (
        'wallet-card-payment' in text
        or ('کارت به کارت' in text and 'کیف پول' in text)
    )


def is_wallet_bank_withdrawal_ticket(ticket):
    text = f'{getattr(ticket, "subject", "")}\n{getattr(ticket, "message", "")}'.lower()
    if 'wallet-bank-withdrawal' in text:
        return True
    if 'درخواست برداشت از کیف پول' in text:
        return True
    return (
        'برداشت' in text
        and 'کیف پول' in text
        and ('شبا' in text or 'بانک' in text or 'iban' in text)
    )


def parse_wallet_id_from_ticket(ticket):
    message = getattr(ticket, 'message', '') or ''
    match = re.search(r'wallet_id\s*:\s*(\d+)', message, flags=re.IGNORECASE)
    if not match:
        match = re.search(r'شناسه کیف پول مقصد\s*:\s*(\d+)', message)
    if not match:
        return None
    return int(match.group(1))


def parse_wallet_amount_from_ticket(ticket):
    message = getattr(ticket, 'message', '') or ''
    patterns = [
        r'withdraw_amount\s*:\s*([0-9.,]+)',
        r'مبلغ\s*پرداخت\s*[:：]?\s*([0-9٬،,\s]+)',
        r'مبلغ\s*واریز\s*[:：]?\s*([0-9٬،,\s]+)',
        r'مبلغ\s*شارژ\s*[:：]?\s*([0-9٬،,\s]+)',
        r'amount\s*[:：]?\s*([0-9.,]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if not match:
            continue
        raw = (
            match.group(1)
            .replace(',', '')
            .replace('٬', '')
            .replace('،', '')
            .replace(' ', '')
        )
        try:
            value = Decimal(raw)
        except Exception:
            continue
        if value > 0:
            return value
    return Decimal('0')


def is_payment_support_ticket(ticket):
    """Payment deposit (card-to-card) or bank withdrawal tickets that need SMS alerts."""
    return is_wallet_card_payment_ticket(ticket) or is_wallet_bank_withdrawal_ticket(ticket)


def hq_ticket_alert_kind(ticket):
    """Return alert label for payment / withdrawal / registration tickets, else None."""
    if not ticket:
        return None
    if getattr(ticket, 'is_registration_request', False):
        return 'ثبت‌نام'
    if is_wallet_bank_withdrawal_ticket(ticket):
        return 'برداشت'
    if is_wallet_card_payment_ticket(ticket):
        return 'پرداخت'
    return None


def should_alert_hq_ticket_sms(ticket):
    return hq_ticket_alert_kind(ticket) is not None


def simple_support_users():
    return User.objects.filter(
        platform_role=User.PlatformRoles.HQ_SUPPORT,
        is_active=True,
        is_deleted=False,
    )


def hq_alert_users():
    """HQ supporters + managers who should get ticket SMS alerts."""
    return User.objects.filter(
        platform_role__in=[
            User.PlatformRoles.HQ_SUPPORT,
            User.PlatformRoles.HQ_ADMIN,
            User.PlatformRoles.HQ_PROJECT_MANAGER,
            User.PlatformRoles.HQ_FINANCE,
        ],
        is_active=True,
        is_deleted=False,
    )


def hq_ticket_visibility_q(user):
    """
    Non-HQ users only see unassigned tickets or tickets assigned to them.
    HQ roles bypass this filter in apply_hq_ticket_visibility.
    """
    return Q(assigned_to__isnull=True) | Q(assigned_to=user)


def apply_hq_ticket_visibility(queryset, user):
    """
    All HQ staff can see every ticket (for shared supervision).
    Claim/referral only marks who is responsible to reply; it does not hide the ticket.
    """
    role = getattr(user, 'platform_role', None) or ''
    username = getattr(user, 'username', '') or ''
    if role in (
        User.PlatformRoles.HQ_ADMIN,
        User.PlatformRoles.HQ_SUPPORT,
        User.PlatformRoles.HQ_PROJECT_MANAGER,
        User.PlatformRoles.HQ_FINANCE,
    ) or username in {'karimi', 'dehestani'}:
        return queryset
    return queryset.filter(hq_ticket_visibility_q(user)).distinct()


def claim_ticket_if_unassigned(ticket, user):
    """Take ownership when an HQ agent first acts on a pooled ticket."""
    if ticket is None or user is None:
        return False
    if ticket.assigned_to_id:
        return False
    ticket.assigned_to = user
    return True


def refer_ticket_to_user(ticket, assignee_id):
    if not ticket or not assignee_id:
        return None
    assignee = User.objects.filter(
        id=assignee_id,
        platform_role__in=[User.PlatformRoles.HQ_ADMIN, User.PlatformRoles.HQ_SUPPORT],
        is_active=True,
        is_deleted=False,
    ).first()
    if not assignee:
        return None
    ticket.assigned_to = assignee
    return assignee


def _collect_hq_alert_phones():
    phones = []
    for user in hq_alert_users().only('id', 'phone'):
        phone = normalize_phone(getattr(user, 'phone', '') or '')
        if phone and phone not in phones:
            phones.append(phone)
    return phones


def _hq_ticket_sms_cache_key(ticket_id):
    return f'hq_ticket_sms_notified:{int(ticket_id)}'


def notify_hq_alert_ticket_sms(ticket_or_id, *, force=False):
    """
    One SMS blast to every active HQ team member (simple support + managers).
    Idempotent per ticket so the create webhook and legacy callers do not double-send.
    """
    if ticket_or_id is None:
        return {'sent': False, 'reason': 'missing_ticket'}

    if isinstance(ticket_or_id, SupportTicket):
        ticket = ticket_or_id
    else:
        ticket = SupportTicket.objects.filter(pk=ticket_or_id).first()
    if not ticket:
        return {'sent': False, 'reason': 'ticket_not_found'}

    kind = hq_ticket_alert_kind(ticket)
    if not kind:
        return {'sent': False, 'reason': 'not_alert_ticket'}

    cache_key = _hq_ticket_sms_cache_key(ticket.pk)
    if not force and not cache.add(cache_key, '1', timeout=_HQ_TICKET_SMS_CACHE_TTL_SECONDS):
        return {'sent': False, 'reason': 'already_notified'}

    phones = _collect_hq_alert_phones()
    if not phones:
        cache.delete(cache_key)
        return {'sent': False, 'reason': 'no_hq_phones'}

    body = f'تیکت {kind} #{ticket.id} ثبت شد\nسامانه کارنوواش'
    try:
        result = send_provider_sms(None, body, phones)
        if not result.get('ok'):
            cache.delete(cache_key)
        return result
    except Exception as exc:
        cache.delete(cache_key)
        return {'sent': False, 'error': str(exc)}


def send_payment_ticket_sms_to_simple_supporters(ticket):
    """Backward-compatible alias — payment/withdrawal alerts to the full HQ team."""
    return notify_hq_alert_ticket_sms(ticket)


def send_registration_ticket_sms_to_hq(ticket):
    """Backward-compatible alias — registration alerts to the full HQ team."""
    return notify_hq_alert_ticket_sms(ticket)


def _format_registration_document_status(documents_count, document_names=None):
    names = [str(name or '').strip() for name in (document_names or []) if str(name or '').strip()]
    if documents_count <= 0:
        return (
            '  • وضعیت: بارگذاری نشده\n'
            '  • توضیح: متقاضی مدرک شناسایی کسب‌وکار پیوست نکرده است.'
        )
    lines = [f'  • وضعیت: {documents_count} فایل پیوست شده']
    for index, name in enumerate(names[:10], start=1):
        lines.append(f'  • فایل {index}: {name}')
    if len(names) > 10:
        lines.append(f'  • ... و {len(names) - 10} فایل دیگر')
    return '\n'.join(lines)


def build_registration_ticket_subject(carwash_name):
    clean_name = str(carwash_name or '').strip() or 'کارواش جدید'
    return f'درخواست تایید ثبت‌نام | {clean_name}'


def build_registration_ticket_body(*, tenant, manager, documents_count=0, document_names=None, submitted_at=None):
    submitted_at = submitted_at or timezone.localtime(timezone.now())
    submitted_label = submitted_at.strftime('%Y/%m/%d %H:%M')
    manager_name = str(getattr(manager, 'full_name', '') or getattr(manager, 'username', '') or '-').strip()
    username = str(getattr(manager, 'username', '') or '-').strip()
    phone = str(getattr(manager, 'phone', '') or '-').strip()
    carwash_name = str(getattr(tenant, 'name', '') or '-').strip()
    slug = str(getattr(tenant, 'slug', '') or '-').strip()
    address = str(getattr(tenant, 'address', '') or '').strip() or 'ثبت نشده'
    document_block = _format_registration_document_status(documents_count, document_names)

    return (
        '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
        'درخواست ثبت‌نام کارواش جدید\n'
        '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n'
        '▸ زمان ثبت درخواست\n'
        f'  • {submitted_label}\n\n'
        '▸ اطلاعات کارواش\n'
        f'  • نام: {carwash_name}\n'
        f'  • شناسه: {slug}\n'
        f'  • آدرس: {address}\n'
        '  • وضعیت حساب: غیرفعال (منتظر تایید HQ)\n\n'
        '▸ اطلاعات مدیر\n'
        f'  • نام: {manager_name}\n'
        f'  • نام کاربری: {username}\n'
        f'  • موبایل: {phone}\n'
        '  • نقش: مدیر کارواش\n\n'
        '▸ مدارک شناسایی کسب‌وکار\n'
        f'{document_block}\n\n'
        '▸ اقدام پشتیبانی\n'
        '  • مدارک و اطلاعات را بررسی کنید.\n'
        '  • در صورت تایید، گزینه «تایید و فعال‌سازی» را بزنید.\n'
        '  • پس از تایید، پیامک فعال‌سازی برای مدیر ارسال می‌شود.'
    )


def build_registration_approval_ticket_note(*, carwash_name, username, reviewer_name='', sms_sent=False, sms_error=''):
    reviewer = str(reviewer_name or '').strip() or 'تیم پشتیبانی HQ'
    sms_line = '  • پیامک فعال‌سازی: ارسال شد.'
    if not sms_sent:
        sms_line = f'  • پیامک فعال‌سازی: ارسال نشد ({str(sms_error or "-").strip()})'
    return (
        '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
        'تایید ثبت‌نام کارواش\n'
        '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n'
        '▸ نتیجه بررسی\n'
        '  • وضعیت: تایید و فعال‌سازی شد\n'
        f'  • بررسی‌کننده: {reviewer}\n\n'
        '▸ اطلاعات فعال‌شده\n'
        f'  • کارواش: {str(carwash_name or "-").strip()}\n'
        f'  • نام کاربری مدیر: {str(username or "-").strip()}\n'
        f'{sms_line}\n\n'
        '▸ پیام برای متقاضی\n'
        '  • تیم پشتیبانی سامانه کارنوواش درخواست ثبت‌نام را تایید کرد.'
    )
