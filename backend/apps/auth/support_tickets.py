from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from apps.notifications.services import normalize_phone, send_provider_sms

from .models import SupportTicket, User


SUPPORT_TICKET_AUTO_CLOSE_AFTER_DAYS = 3


def close_stale_support_tickets(*, now=None):
    current = now or timezone.now()
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
    return 'wallet-bank-withdrawal' in text


def is_payment_support_ticket(ticket):
    """Payment deposit (card-to-card) or bank withdrawal tickets that need SMS alerts."""
    return is_wallet_card_payment_ticket(ticket) or is_wallet_bank_withdrawal_ticket(ticket)


def simple_support_users():
    return User.objects.filter(
        platform_role=User.PlatformRoles.HQ_SUPPORT,
        is_active=True,
        is_deleted=False,
    )


def hq_ticket_visibility_q(user):
    """
    Unassigned tickets (pool) are visible to every active HQ support + HQ admin.
    After claim/referral, the ticket is only visible to the assignee.
    """
    return Q(assigned_to__isnull=True) | Q(assigned_to=user)


def apply_hq_ticket_visibility(queryset, user):
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


def send_payment_ticket_sms_to_simple_supporters(ticket):
    """
    SMS only for payment deposit/withdrawal tickets, and only to simple HQ supporters.
    Manual/general tickets do not trigger SMS.
    """
    if not ticket or not is_payment_support_ticket(ticket):
        return {'sent': False, 'reason': 'not_payment_ticket'}

    phones = []
    for supporter in simple_support_users().only('id', 'phone'):
        phone = normalize_phone(getattr(supporter, 'phone', '') or '')
        if phone and phone not in phones:
            phones.append(phone)

    if not phones:
        return {'sent': False, 'reason': 'no_support_phones'}

    if is_wallet_bank_withdrawal_ticket(ticket):
        label = 'تیکت برداشت جدید ثبت شد'
    else:
        label = 'تیکت پرداخت جدید ثبت شد'

    tenant_name = ticket.tenant.name if getattr(ticket, 'tenant_id', None) else '-'
    body = f'{label}\nشماره تیکت: {ticket.id}\nکارواش: {tenant_name}'
    try:
        return send_provider_sms(None, body, phones)
    except Exception as exc:
        return {'sent': False, 'error': str(exc)}
