from django.conf import settings
from django.db import models


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ReportSnapshot(TimestampedModel):
    class ReportType(models.TextChoices):
        OVERALL = 'overall', 'Overall'
        CARWASH_SHARE = 'carwash_share', 'Carwash Share'
        WORKER_SHARE = 'worker_share', 'Worker Share'
        TIPS = 'tips', 'Tips'
        ATTENDANCE = 'attendance', 'Attendance'

    report_type = models.CharField(max_length=40, choices=ReportType.choices)
    period_start = models.DateField()
    period_end = models.DateField()
    filters = models.JSONField(default=dict, blank=True)
    summary_data = models.JSONField(default=dict, blank=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='report_snapshots_generated',
    )

    class Meta:
        ordering = ['-period_end', '-id']
        indexes = [models.Index(fields=['report_type', 'period_start', 'period_end'])]
