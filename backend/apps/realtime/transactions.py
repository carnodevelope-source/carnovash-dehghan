"""Transactional boundary for models that publish a live event via signals."""

from __future__ import annotations

from django.conf import settings
from django.db import transaction


class TransactionalLiveModelMixin:
    """Keep a producer's model write and its signal-created outbox row atomic.

    Signal receivers run during ``Model.save()``/``Model.delete()``. When V2
    outbox is enabled, this mixin opens the outer transaction before Django
    emits those signals, so the business row and ``LiveOutbox`` row either both
    commit or both roll back. Existing explicit ``transaction.atomic()`` blocks
    remain the shared outer boundary; the mixin never creates a second one.

    QuerySet.bulk_create()/update() deliberately bypass Django signals and do
    not claim to emit a live event. Any future bulk producer must use an
    explicit service transaction and outbox write.
    """

    @staticmethod
    def _outbox_transaction_enabled(using: str | None) -> bool:
        return bool(
            getattr(settings, 'LIVE_OUTBOX_ENABLED', False)
            and not transaction.get_connection(using=using).in_atomic_block
        )

    def save(self, *args, **kwargs):
        using = kwargs.get('using')
        if not self._outbox_transaction_enabled(using):
            return super().save(*args, **kwargs)
        with transaction.atomic(using=using):
            return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        using = kwargs.get('using')
        if not self._outbox_transaction_enabled(using):
            return super().delete(*args, **kwargs)
        with transaction.atomic(using=using):
            return super().delete(*args, **kwargs)
