from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.auth.models import SupportTicket, SupportTicketMessage
from apps.auth.serializers import SupportTicketListSerializer
from apps.auth.support_tickets import (
    apply_hq_ticket_visibility,
    is_wallet_bank_withdrawal_ticket,
    parse_wallet_amount_from_ticket,
    parse_wallet_id_from_ticket,
)
from apps.payments.models import Wallet


class Command(BaseCommand):
    help = (
        'Diagnose HQ ticket visibility and optionally create a sample bank-withdraw ticket '
        'to verify it appears in مرکز تیکت.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-sample',
            action='store_true',
            help='Create one sample wallet-bank-withdrawal ticket for the first active tenant.',
        )
        parser.add_argument(
            '--amount',
            type=int,
            default=1000,
            help='Amount for sample withdraw ticket (default 1000).',
        )

    def handle(self, *args, **options):
        user_model = get_user_model()
        total = SupportTicket.objects.count()
        open_count = SupportTicket.objects.filter(status=SupportTicket.Status.OPEN).count()
        withdraw_count = SupportTicket.objects.filter(message__icontains='wallet-bank-withdrawal').count()
        deposit_count = SupportTicket.objects.filter(message__icontains='wallet-card-payment').count()

        self.stdout.write('=== Ticket inventory ===')
        self.stdout.write(f'total={total} open={open_count} withdraw={withdraw_count} deposit={deposit_count}')

        hq_users = list(
            user_model.objects.filter(
                platform_role__in=['hq_admin', 'hq_support'],
                is_active=True,
                is_deleted=False,
            ).order_by('id')
        )
        self.stdout.write('=== HQ users ===')
        if not hq_users:
            self.stdout.write(self.style.ERROR('No active HQ admin/support users found.'))
        for user in hq_users:
            visible = apply_hq_ticket_visibility(
                SupportTicket.objects.filter(tenant__exclude_from_hq_reports=False),
                user,
            ).count()
            self.stdout.write(
                f'- id={user.id} username={user.username} role={user.platform_role} visible_tickets={visible}'
            )

        excluded = list(
            SupportTicket.objects.filter(tenant__exclude_from_hq_reports=True)
            .values_list('id', 'tenant_id', 'subject')[:20]
        )
        if excluded:
            self.stdout.write(self.style.WARNING(f'Tickets hidden by exclude_from_hq_reports: {excluded}'))

        sample_ticket = None
        if options.get('create_sample'):
            sample_ticket = self._create_sample_ticket(amount=options['amount'])
            self.stdout.write(self.style.SUCCESS(f'Created sample withdraw ticket id={sample_ticket.id}'))

        focus = sample_ticket or SupportTicket.objects.order_by('-id').first()
        if not focus:
            self.stdout.write(self.style.WARNING('No tickets to inspect.'))
            return

        payload = SupportTicketListSerializer(focus).data
        self.stdout.write('=== Latest/sample ticket payload ===')
        for key in [
            'id',
            'subject',
            'status',
            'priority',
            'tenant',
            'tenant_name',
            'is_wallet_bank_withdrawal',
            'is_wallet_card_payment',
            'can_wallet_withdraw',
            'can_wallet_transfer',
            'suggested_wallet_amount',
            'wallet_id',
        ]:
            self.stdout.write(f'{key}={payload.get(key)}')

        self.stdout.write(
            f'detect_withdraw={is_wallet_bank_withdrawal_ticket(focus)} '
            f'parsed_wallet_id={parse_wallet_id_from_ticket(focus)} '
            f'parsed_amount={parse_wallet_amount_from_ticket(focus)}'
        )

        if hq_users:
            visible_ids = list(
                apply_hq_ticket_visibility(
                    SupportTicket.objects.filter(tenant__exclude_from_hq_reports=False),
                    hq_users[0],
                ).values_list('id', flat=True)[:30]
            )
            in_hq = focus.id in visible_ids or SupportTicket.objects.filter(
                pk=focus.id,
                tenant__exclude_from_hq_reports=False,
            ).exists()
            if in_hq:
                self.stdout.write(self.style.SUCCESS(f'Ticket #{focus.id} SHOULD appear in HQ مرکز تیکت.'))
            else:
                self.stdout.write(self.style.ERROR(f'Ticket #{focus.id} will NOT appear in HQ list. Check tenant.exclude_from_hq_reports.'))

    @transaction.atomic
    def _create_sample_ticket(self, *, amount):
        user_model = get_user_model()
        manager = (
            user_model.objects.filter(role='manager', is_active=True, tenant__isnull=False)
            .select_related('tenant')
            .order_by('id')
            .first()
        )
        if not manager or not manager.tenant_id:
            raise SystemExit('No manager with tenant found to create sample ticket.')

        wallet = (
            Wallet.objects.filter(tenant=manager.tenant, is_active=True)
            .order_by('id')
            .first()
        )
        if not wallet:
            wallet = Wallet.objects.create(
                tenant=manager.tenant,
                name='کیف پول اصلی',
                wallet_type=Wallet.WalletType.BANK,
                balance=Decimal('0'),
                is_active=True,
            )

        now = timezone.now()
        amount_dec = Decimal(str(amount))
        message = '\n'.join([
            'wallet-bank-withdrawal',
            f'wallet_id: {wallet.id}',
            f'withdraw_amount: {amount_dec}',
            'iban: IR000000000000000000000001',
            'account_holder: sample',
            f'wallet_name: {wallet.name}',
            f'tenant_id: {manager.tenant_id}',
            f'tenant_name: {manager.tenant.name}',
            'description: sample-verify',
            'wallet_debited: no',
            '',
            f'درخواست برداشت {amount_dec:,.0f} تومان از کیف پول «{wallet.name}» (نمونه تست سرور).',
        ])
        ticket = SupportTicket.objects.create(
            tenant=manager.tenant,
            created_by=manager,
            subject='درخواست برداشت از کیف پول به حساب بانکی',
            message=message,
            category=SupportTicket.Category.FINANCIAL,
            priority=SupportTicket.Priority.URGENT,
            status=SupportTicket.Status.OPEN,
            assigned_to=None,
            last_message_at=now,
        )
        SupportTicketMessage.objects.create(ticket=ticket, sender=manager, body=message)
        return ticket
