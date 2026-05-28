from django.conf import settings
from django.db import models


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class NotificationLog(TimestampedModel):
    class Channel(models.TextChoices):
        SMS = 'sms', 'SMS'
        PUSH = 'push', 'Push'
        EMAIL = 'email', 'Email'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SENT = 'sent', 'Sent'
        FAILED = 'failed', 'Failed'

    vehicle_entry = models.ForeignKey(
        'vehicles.VehicleEntry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notification_logs',
    )
    channel = models.CharField(max_length=20, choices=Channel.choices)
    recipient = models.CharField(max_length=120)
    template_code = models.CharField(max_length=60, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    sent_at = models.DateTimeField(null=True, blank=True)
    provider_message_id = models.CharField(max_length=120, blank=True)
    provider_response = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notification_logs_created',
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['channel', 'status', 'created_at'])]
