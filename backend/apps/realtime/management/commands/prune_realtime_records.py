from datetime import timedelta
import logging

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.realtime.models import IdempotencyRecord, LiveOutbox


logger = logging.getLogger(__name__)
LOCK_KEY = 'realtime:prune-records:v1'


def _positive_setting(name, default, *, minimum=1):
    try:
        return max(minimum, int(getattr(settings, name, default)))
    except (TypeError, ValueError):
        return default


def prune_in_bounded_batches(model, *, cutoff, batch_size, max_batches):
    """Delete old rows in short, deterministic transactions.

    Selecting rows with a row lock prevents two command invocations from
    deleting the same batch. The cache lock avoids needless contention when a
    shared cache is configured; the database lock remains the correctness
    mechanism if it is not.
    """
    deleted = 0
    batches = 0
    has_more = False
    for _ in range(max_batches):
        with transaction.atomic():
            ids = list(
                model.objects.filter(created_at__lt=cutoff)
                .order_by('id')
                .select_for_update()
                .values_list('id', flat=True)[:batch_size]
            )
            if not ids:
                break
            model.objects.filter(id__in=ids).delete()
        deleted += len(ids)
        batches += 1
        has_more = len(ids) == batch_size
        if len(ids) < batch_size:
            break
    return deleted, batches, has_more


class Command(BaseCommand):
    help = 'Prune short-retention live outbox and idempotency records.'

    def handle(self, *args, **options):
        # A short lease covers the bounded run. If a node dies, the DB locks
        # are released and a later scheduler tick can resume safely.
        if not cache.add(LOCK_KEY, '1', timeout=300):
            self.stdout.write('Realtime record pruning already running; skipped.')
            return
        now = timezone.now()
        outbox_cutoff = now - timedelta(hours=getattr(settings, 'LIVE_OUTBOX_RETENTION_HOURS', 72))
        idempotency_cutoff = now - timedelta(hours=getattr(settings, 'IDEMPOTENCY_RETENTION_HOURS', 168))
        try:
            outbox_count, outbox_batches, outbox_more = prune_in_bounded_batches(
                LiveOutbox,
                cutoff=outbox_cutoff,
                batch_size=_positive_setting('LIVE_OUTBOX_CLEANUP_BATCH_SIZE', 500),
                max_batches=_positive_setting('LIVE_OUTBOX_CLEANUP_MAX_BATCHES', 20),
            )
            idempotency_count, idempotency_batches, idempotency_more = prune_in_bounded_batches(
                IdempotencyRecord,
                cutoff=idempotency_cutoff,
                batch_size=_positive_setting('IDEMPOTENCY_CLEANUP_BATCH_SIZE', 500),
                max_batches=_positive_setting('IDEMPOTENCY_CLEANUP_MAX_BATCHES', 20),
            )
            logger.info(
                'realtime.cleanup completed outbox_deleted=%s outbox_batches=%s outbox_more=%s '
                'idempotency_deleted=%s idempotency_batches=%s idempotency_more=%s',
                outbox_count, outbox_batches, outbox_more,
                idempotency_count, idempotency_batches, idempotency_more,
            )
            self.stdout.write(
                'Pruned '
                f'{outbox_count} outbox rows in {outbox_batches} batch(es) '
                f'(remaining={outbox_more}) and {idempotency_count} idempotency rows '
                f'in {idempotency_batches} batch(es) (remaining={idempotency_more}).'
            )
        finally:
            cache.delete(LOCK_KEY)
