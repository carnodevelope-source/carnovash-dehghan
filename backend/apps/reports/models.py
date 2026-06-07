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

    tenant = models.ForeignKey(
        'cw_auth.CarWash',
        on_delete=models.CASCADE,
        related_name='report_snapshots',
        null=True,
        blank=True,
    )
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


class WorkerPayoutTransaction(TimestampedModel):
    class Kind(models.TextChoices):
        WAGE_PAYMENT = 'wage_payment', 'Wage Payment'
        TIP_PAYMENT = 'tip_payment', 'Tip Payment'
        BONUS = 'bonus', 'Bonus'
        PENALTY = 'penalty', 'Penalty'

    tenant = models.ForeignKey(
        'cw_auth.CarWash',
        on_delete=models.CASCADE,
        related_name='worker_payout_transactions',
        null=True,
        blank=True,
    )
    worker = models.ForeignKey(
        'workers.WorkerProfile',
        on_delete=models.CASCADE,
        related_name='payout_transactions',
    )
    vehicle_job = models.ForeignKey(
        'vehicles.VehicleJob',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='worker_payout_transactions',
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='worker_payout_transactions_created',
    )

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['worker', 'kind', 'created_at']),
            models.Index(fields=['tenant', 'created_at']),
        ]
