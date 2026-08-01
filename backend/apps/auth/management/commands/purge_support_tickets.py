from django.core.management.base import BaseCommand
from django.db import transaction

from apps.auth.models import SupportTicket, SupportTicketAttachment, SupportTicketMessage


class Command(BaseCommand):
    help = (
        'Delete all support tickets (and related messages/attachments) to clear stale '
        'or conflicting ticket data. Use on server after deploy if HQ ticket inbox is broken.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Confirm deletion without interactive prompt.',
        )
        parser.add_argument(
            '--tenant-id',
            type=int,
            default=None,
            help='Only delete tickets for one carwash/tenant id.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        queryset = SupportTicket.objects.all()
        tenant_id = options.get('tenant_id')
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        ticket_count = queryset.count()
        if ticket_count == 0:
            self.stdout.write(self.style.WARNING('No support tickets found.'))
            return

        if not options.get('yes'):
            self.stderr.write(
                self.style.ERROR(
                    f'Refusing to delete {ticket_count} ticket(s). Re-run with --yes to confirm.'
                )
            )
            return

        ticket_ids = list(queryset.values_list('id', flat=True))
        messages_deleted, _ = SupportTicketMessage.objects.filter(ticket_id__in=ticket_ids).delete()
        attachments_deleted, _ = SupportTicketAttachment.objects.filter(ticket_id__in=ticket_ids).delete()
        tickets_deleted, _ = queryset.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f'Purged tickets={tickets_deleted} messages={messages_deleted} '
                f'attachments={attachments_deleted}'
                + (f' (tenant_id={tenant_id})' if tenant_id else ' (all tenants)')
            )
        )
