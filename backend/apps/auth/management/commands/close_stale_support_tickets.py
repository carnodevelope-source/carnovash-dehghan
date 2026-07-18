from django.core.management.base import BaseCommand

from apps.auth.support_tickets import close_stale_support_tickets


class Command(BaseCommand):
    help = 'Close support tickets that have not received a message for 3 days.'

    def handle(self, *args, **options):
        closed_count = close_stale_support_tickets()
        self.stdout.write(self.style.SUCCESS(f'Closed {closed_count} stale support ticket(s).'))
