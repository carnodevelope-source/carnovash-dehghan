from django.conf import settings
from django.db import models


class LiveOutbox(models.Model):
    """A short-retention replay cursor; never a source of business state."""

    tenant_id = models.BigIntegerField(null=True, blank=True)
    actor_user_id = models.BigIntegerField(null=True, blank=True)
    event_type = models.CharField(max_length=80)
    entity_type = models.CharField(max_length=40, blank=True)
    entity_id = models.CharField(max_length=100, blank=True)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['tenant_id', 'id'], name='live_outbox_tenant_id_idx'),
            models.Index(fields=['created_at'], name='live_outbox_created_idx'),
        ]


class IdempotencyRecord(models.Model):
    """Caches a completed unsafe request, scoped to its authenticated caller."""

    # MySQL UNIQUE allows multiple NULL values; use zero for HQ/no-tenant
    # callers so (tenant, user, key) remains genuinely unique.
    tenant_id = models.BigIntegerField(default=0)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='idempotency_records',
    )
    key = models.CharField(max_length=128)
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=255)
    request_hash = models.CharField(max_length=64)
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    response_json = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant_id', 'user', 'key'],
                name='uniq_idempotency_tenant_user_key',
            )
        ]
        indexes = [models.Index(fields=['created_at'], name='idempotency_created_idx')]
