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

    tenant = models.ForeignKey(
        'cw_auth.CarWash',
        on_delete=models.CASCADE,
        related_name='notification_logs',
        null=True,
        blank=True,
    )
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


class SmsTemplate(TimestampedModel):
    tenant = models.ForeignKey(
        'cw_auth.CarWash',
        on_delete=models.CASCADE,
        related_name='sms_templates',
        null=True,
        blank=True,
    )
    code = models.CharField(max_length=60)
    title = models.CharField(max_length=120)
    body = models.TextField()
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sms_templates_created',
    )

    class Meta:
        ordering = ['display_order', 'title', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'code'],
                name='uniq_sms_template_code_per_tenant',
            ),
        ]


class CustomerGroup(TimestampedModel):
    class Mode(models.TextChoices):
        MANUAL = 'manual', 'Manual'
        SMART = 'smart', 'Smart'

    tenant = models.ForeignKey(
        'cw_auth.CarWash',
        on_delete=models.CASCADE,
        related_name='customer_groups',
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    mode = models.CharField(max_length=20, choices=Mode.choices, default=Mode.MANUAL)
    member_keys = models.JSONField(default=list, blank=True)
    rules = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customer_groups_created',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customer_groups_updated',
    )

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['tenant', 'is_active', 'created_at']),
        ]


class ImportedCustomer(TimestampedModel):
    tenant = models.ForeignKey(
        'cw_auth.CarWash',
        on_delete=models.CASCADE,
        related_name='imported_customers',
    )
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20)
    car_model = models.CharField(max_length=120, blank=True)
    car_color = models.CharField(max_length=60, blank=True)
    plate_number = models.CharField(max_length=40, blank=True)
    notes = models.TextField(blank=True)
    source = models.CharField(max_length=40, default='excel')
    imported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='imported_customers_created',
    )

    class Meta:
        ordering = ['-updated_at', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'phone'],
                name='uniq_imported_customer_phone_per_tenant',
            ),
        ]
        indexes = [
            models.Index(fields=['tenant', 'phone']),
        ]
