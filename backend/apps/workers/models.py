from django.conf import settings
from django.db import models


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class WorkerProfile(TimestampedModel):
    class PaymentType(models.TextChoices):
        PERCENT = 'percent', 'Percent'
        FIXED = 'fixed', 'Fixed'
        HOURLY = 'hourly', 'Hourly'
    
    class LoadStatus(models.TextChoices):
        FREE = 'free', 'Free'
        NORMAL = 'normal', 'Normal'
        BUSY = 'busy', 'Busy'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='worker_profile'
    )
    tenant = models.ForeignKey(
        'cw_auth.CarWash',
        on_delete=models.CASCADE,
        related_name='worker_profiles',
        null=True,
        blank=True,
    )
    code = models.CharField(max_length=30, unique=True, null=True, blank=True)
    national_id = models.CharField(max_length=20, blank=True)
    default_commission_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    default_fixed_wage = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    default_hourly_wage = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    insurance_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_type = models.CharField(max_length=20, choices=PaymentType.choices, default=PaymentType.PERCENT)
    tip_share_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    last_assigned_at = models.DateTimeField(null=True, blank=True)
    is_available = models.BooleanField(default=True)
    load_status = models.CharField(
        max_length=20, choices=LoadStatus.choices, default=LoadStatus.FREE
    )
    active_jobs_count = models.PositiveIntegerField(default=0)
    attendance_token = models.CharField(max_length=120, unique=True, null=True, blank=True)
    started_at = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='worker_profiles_deleted',
    )
    has_entrusted_item = models.BooleanField(default=False)
    entrusted_items = models.JSONField(default=list, blank=True)
    entrusted_item_description = models.TextField(blank=True)
    entrusted_item_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    entrusted_item_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ['user__full_name', 'user__username']

    def __str__(self) -> str:
        return self.user.full_name or self.user.username


class WorkerAttendance(TimestampedModel):
    class EventType(models.TextChoices):
        IN = 'in', 'In'
        OUT = 'out', 'Out'

    worker = models.ForeignKey(
        WorkerProfile, on_delete=models.CASCADE, related_name='attendance_events'
    )
    tenant = models.ForeignKey(
        'cw_auth.CarWash',
        on_delete=models.CASCADE,
        related_name='worker_attendances',
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=10, choices=EventType.choices)
    event_at = models.DateTimeField()
    source = models.CharField(max_length=40, default='link')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_info = models.CharField(max_length=255, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['-event_at']
        indexes = [
            models.Index(fields=['worker', 'event_at']),
            models.Index(fields=['event_type', 'event_at']),
        ]
