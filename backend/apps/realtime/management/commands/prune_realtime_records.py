from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.realtime.models import IdempotencyRecord, LiveOutbox


class Command(BaseCommand):
    help = 'Prune short-retention live outbox and idempotency records.'

    def handle(self, *args, **options):
        now = timezone.now()
        outbox_cutoff = now - timedelta(hours=getattr(settings, 'LIVE_OUTBOX_RETENTION_HOURS', 72))
        idempotency_cutoff = now - timedelta(hours=getattr(settings, 'IDEMPOTENCY_RETENTION_HOURS', 168))
        outbox_count, _ = LiveOutbox.objects.filter(created_at__lt=outbox_cutoff).delete()
        idempotency_count, _ = IdempotencyRecord.objects.filter(created_at__lt=idempotency_cutoff).delete()
        self.stdout.write(f'Pruned {outbox_count} outbox and {idempotency_count} idempotency records.')
