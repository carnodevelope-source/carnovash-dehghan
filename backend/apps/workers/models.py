from django.conf import settings
from django.db import models


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class WorkerProfile(TimestampedModel):
    
    class LoadStatus(models.TextChoices):
        FREE = 'free', 'Free'
        NORMAL = 'normal', 'Normal'
        BUSY = 'busy', 'Busy'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='worker_profile'
    )
    code = models.CharField(max_length=30, unique=True, null=True, blank=True)
    national_id = models.CharField(max_length=20, blank=True)
    default_commission_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    default_fixed_wage = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_available = models.BooleanField(default=True)
    load_status = models.CharField(
        max_length=20, choices=LoadStatus.choices, default=LoadStatus.FREE
    )
    active_jobs_count = models.PositiveIntegerField(default=0)
    attendance_token = models.CharField(max_length=120, unique=True, null=True, blank=True)
    notes = models.TextField(blank=True)

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
