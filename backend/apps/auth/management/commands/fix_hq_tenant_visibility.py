from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from django.utils import timezone

from apps.auth.models import CarWash, SupportTicket


class Command(BaseCommand):
    help = (
        'List carwashes hidden from HQ by exclude_from_hq_reports, and optionally '
        'include them back so their tickets appear in مرکز تیکت.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--include-all-active',
            action='store_true',
            help='Set exclude_from_hq_reports=False for every active carwash.',
        )
        parser.add_argument(
            '--include-name-contains',
            type=str,
            default='',
            help='Include active carwashes whose name/slug contains this text (e.g. میلان).',
        )
        parser.add_argument(
            '--tenant-id',
            type=int,
            default=None,
            help='Include only this tenant id.',
        )
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Apply changes. Without this flag, only prints the current state.',
        )

    def handle(self, *args, **options):
        rows = (
            CarWash.objects.all()
            .annotate(ticket_count=Count('support_tickets'))
            .order_by('id')
        )
        self.stdout.write('=== Carwash HQ visibility ===')
        hidden = []
        for row in rows:
            mark = 'HIDDEN' if row.exclude_from_hq_reports else 'visible'
            self.stdout.write(
                f'- id={row.id} [{mark}] active={row.is_active} tickets={row.ticket_count} '
                f'name={row.name} slug={row.slug}'
            )
            if row.exclude_from_hq_reports:
                hidden.append(row)

        if not options['include_all_active'] and not options['include_name_contains'] and not options['tenant_id']:
            if hidden:
                self.stdout.write(
                    self.style.WARNING(
                        f'{len(hidden)} carwash(es) are hidden from HQ tickets/reports. '
                        'Re-run with --include-all-active --yes or --include-name-contains میلان --yes'
                    )
                )
            else:
                self.stdout.write(self.style.SUCCESS('No carwash is hidden from HQ.'))
            return

        qs = CarWash.objects.filter(exclude_from_hq_reports=True)
        if options['tenant_id']:
            qs = qs.filter(pk=options['tenant_id'])
        if options['include_all_active']:
            qs = qs.filter(is_active=True)
        if options['include_name_contains']:
            text = options['include_name_contains'].strip()
            qs = qs.filter(Q(name__icontains=text) | Q(slug__icontains=text))

        qs = qs.distinct()
        count = qs.count()
        if count == 0:
            self.stdout.write(self.style.WARNING('No matching hidden carwash to include.'))
            return

        if not options['yes']:
            self.stdout.write(
                self.style.ERROR(
                    f'Would include {count} carwash(es). Re-run with --yes to apply.'
                )
            )
            for row in qs.order_by('id'):
                self.stdout.write(f'  - id={row.id} {row.name}')
            return

        updated = qs.update(exclude_from_hq_reports=False, updated_at=timezone.now())
        visible_tickets = SupportTicket.objects.filter(tenant__exclude_from_hq_reports=False).count()
        self.stdout.write(
            self.style.SUCCESS(
                f'Included {updated} carwash(es) into HQ. Visible tickets now={visible_tickets}'
            )
        )
