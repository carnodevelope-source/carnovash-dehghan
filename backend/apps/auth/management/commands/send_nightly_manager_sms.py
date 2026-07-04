from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.auth.nightly_sms import dispatch_due_nightly_manager_summaries


class Command(BaseCommand):
    help = 'Send a short nightly SMS summary to each carwash manager.'

    def add_arguments(self, parser):
        parser.add_argument('--date', type=str, help='Gregorian date in YYYY-MM-DD format. Default: previous local day.')

    def handle(self, *args, **options):
        target_date = options.get('date')
        if target_date:
            day = datetime.strptime(target_date, '%Y-%m-%d').date()
        else:
            day = timezone.localdate() - timedelta(days=1)

        sent_count = dispatch_due_nightly_manager_summaries(target_day=day, force=True)
        self.stdout.write(self.style.SUCCESS(f'Sent nightly summary to {sent_count} manager(s).'))
