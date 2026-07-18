from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from .models import SupportTicket


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
