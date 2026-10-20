from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.reports.monthly_wages import accrue_monthly_wages_for_day


class Command(BaseCommand):
    help = 'Accrue monthly wages for monthly-paid workers at the end of a Jalali month.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Target Gregorian date in YYYY-MM-DD format.',
        )

    def handle(self, *args, **options):
        target_date = options.get('date')

        if target_date:
            try:
                day = datetime.strptime(
                    target_date,
                    '%Y-%m-%d',
                ).date()
            except ValueError as exc:
                raise CommandError(
                    'Invalid date. Use YYYY-MM-DD format.'
                ) from exc
        else:
            day = timezone.localdate()

        created_count = accrue_monthly_wages_for_day(day)

        self.stdout.write(
            self.style.SUCCESS(
                f'Monthly wage accrual completed. '
                f'Date: {day} | Created: {created_count}'
            )
        )