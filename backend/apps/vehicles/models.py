from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CustomerProfile(TimestampedModel):
    class Gender(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'

    tenant = models.ForeignKey(
        'cw_auth.CarWash',
        on_delete=models.CASCADE,
        related_name='customers',
        null=True,
        blank=True,
    )
    phone = models.CharField(max_length=20, unique=True, db_index=True)
    full_name = models.CharField(max_length=120, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True, default='')
    yearly_score = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    score_year = models.PositiveSmallIntegerField(default=1400)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self) -> str:
        return f'{self.phone} - {self.full_name or "Customer"}'


class PlateLoyaltyProfile(TimestampedModel):
    tenant = models.ForeignKey(
        'cw_auth.CarWash',
        on_delete=models.CASCADE,
        related_name='plate_loyalty_profiles',
        null=True,
        blank=True,
    )
    plate_number = models.CharField(max_length=20, db_index=True)
    plate_left = models.CharField(max_length=2, blank=True)
    plate_letter = models.CharField(max_length=5, blank=True)
    plate_mid = models.CharField(max_length=3, blank=True)
    plate_right = models.CharField(max_length=2, blank=True)
    score = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    visit_count = models.PositiveIntegerField(default=0)
    cycle_visit_count = models.PositiveIntegerField(default=0)
    last_cycle_started_at = models.DateTimeField(null=True, blank=True)
    first_order_at = models.DateTimeField(null=True, blank=True)
    next_discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'plate_number'],
                name='uniq_plate_loyalty_per_tenant',
            )
        ]

    def __str__(self) -> str:
        return self.plate_number


class VehicleEntry(TimestampedModel):
    class DriverGender(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'

    class TariffType(models.TextChoices):
        TYPE_1 = 'type_1', 'Type 1'
        TYPE_2 = 'type_2', 'Type 2'
        TYPE_3 = 'type_3', 'Type 3'
        TYPE_4 = 'type_4', 'Type 4'

    class PlateType(models.TextChoices):
        CAR = 'car', 'Car'
        MOTORCYCLE = 'motorcycle', 'Motorcycle'

    class Status(models.TextChoices):
        ENTERED = 'entered', 'Entered'
        ASSIGNED = 'assigned', 'Assigned'
        IN_PROGRESS = 'in_progress', 'In Progress'
        READY_TO_SETTLE = 'ready_to_settle', 'Ready To Settle'
        RELEASED = 'released', 'Released'
        CANCELLED = 'cancelled', 'Cancelled'

    class PaymentStatus(models.TextChoices):
        UNPAID = 'unpaid', 'Unpaid'
        PARTIAL = 'partial', 'Partial'
        PAID = 'paid', 'Paid'
        REFUNDED = 'refunded', 'Refunded'

    class PaymentMethod(models.TextChoices):
        POS = 'pos', 'POS'
        CASH = 'cash', 'Cash'
        TRANSFER = 'transfer', 'Transfer'
        CHEQUE = 'cheque', 'Cheque'
        CREDIT = 'credit', 'Credit'
        MANUAL = 'manual', 'Manual'

    class SourceType(models.TextChoices):
        MANUAL = 'manual', 'Manual'
        AI = 'ai', 'AI'
        HYBRID = 'hybrid', 'Hybrid'

    tenant = models.ForeignKey(
        'cw_auth.CarWash',
        on_delete=models.CASCADE,
        related_name='vehicle_entries',
        null=True,
        blank=True,
    )
    plate_number = models.CharField(max_length=20, db_index=True)
    plate_left = models.CharField(max_length=2, blank=True)
    plate_letter = models.CharField(max_length=5, blank=True)
    plate_mid = models.CharField(max_length=3, blank=True)
    plate_right = models.CharField(max_length=2, blank=True)
    plate_type = models.CharField(max_length=20, choices=PlateType.choices, default=PlateType.CAR)
    tariff_type = models.CharField(max_length=20, choices=TariffType.choices, default=TariffType.TYPE_1)
    car_model = models.CharField(max_length=120)
    car_color = models.CharField(max_length=60)
    driver_name = models.CharField(max_length=120)
    driver_gender = models.CharField(max_length=10, choices=DriverGender.choices, blank=True, default='')
    driver_phone = models.CharField(max_length=20, db_index=True)
    sms_notifications_enabled = models.BooleanField(default=True)
    is_piece_wash = models.BooleanField(default=False)
    piece_details = models.TextField(blank=True)
    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vehicle_entries',
    )
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.ENTERED)
    payment_status = models.CharField(
        max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID
    )
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, blank=True, default=''
    )
    intake_source = models.CharField(
        max_length=20, choices=SourceType.choices, default=SourceType.MANUAL
    )
    admission_number = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    ai_confidence = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    check_in_at = models.DateTimeField(auto_now_add=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='vehicle_entries_created',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vehicle_entries_updated',
    )

    class Meta:
        ordering = ['-check_in_at']
        indexes = [
            models.Index(fields=['status', 'check_in_at']),
            models.Index(fields=['payment_status', 'check_in_at']),
            models.Index(fields=['payment_method', 'check_in_at'], name='vehicles_ve_payment_5cc23d_idx'),
        ]

    def __str__(self) -> str:
        return f'{self.plate_number} - {self.driver_name}'

    def _next_daily_admission_number(self):
        now = timezone.localtime(timezone.now())
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        latest = (
            VehicleEntry.objects.filter(
                tenant=self.tenant,
                check_in_at__gte=day_start,
                check_in_at__lt=day_end,
            )
            .exclude(pk=self.pk)
            .aggregate(max_number=models.Max('admission_number'))
            .get('max_number')
        )
        return max(1000, int(latest or 999) + 1)

    def save(self, *args, **kwargs):
        if not self.admission_number:
            self.admission_number = self._next_daily_admission_number()
            update_fields = kwargs.get('update_fields')
            if update_fields is not None:
                kwargs['update_fields'] = set(update_fields) | {'admission_number'}
        super().save(*args, **kwargs)


class BlockedPlate(TimestampedModel):
    tenant = models.ForeignKey(
        'cw_auth.CarWash',
        on_delete=models.CASCADE,
        related_name='blocked_plates',
        null=True,
        blank=True,
    )
    plate_number = models.CharField(max_length=20, db_index=True)
    plate_left = models.CharField(max_length=2, blank=True)
    plate_letter = models.CharField(max_length=5, blank=True)
    plate_mid = models.CharField(max_length=3, blank=True)
    plate_right = models.CharField(max_length=2, blank=True)
    plate_type = models.CharField(max_length=20, choices=VehicleEntry.PlateType.choices, default=VehicleEntry.PlateType.CAR)
    note = models.CharField(max_length=255, blank=True)
    blocked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='blocked_vehicle_plates',
    )

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'plate_number'],
                name='uniq_blocked_plate_per_tenant',
            )
        ]

    def __str__(self) -> str:
        return self.plate_number


class VehicleStatusLog(TimestampedModel):
    tenant = models.ForeignKey(
        'cw_auth.CarWash',
        on_delete=models.CASCADE,
        related_name='vehicle_status_logs',
        null=True,
        blank=True,
    )
    vehicle = models.ForeignKey(
        VehicleEntry, on_delete=models.CASCADE, related_name='status_logs'
    )
    from_status = models.CharField(max_length=30, blank=True)
    to_status = models.CharField(max_length=30)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='vehicle_status_changes',
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['-changed_at']


class VehicleJob(TimestampedModel):
    class WorkerPaymentType(models.TextChoices):
        PERCENT = 'percent', 'Percent'
        FIXED = 'fixed', 'Fixed'
        HOURLY = 'hourly', 'Hourly'

    tenant = models.ForeignKey(
        'cw_auth.CarWash',
        on_delete=models.CASCADE,
        related_name='vehicle_jobs',
        null=True,
        blank=True,
    )
    vehicle = models.OneToOneField(
        VehicleEntry, on_delete=models.CASCADE, related_name='job'
    )
    assigned_worker = models.ForeignKey(
        'workers.WorkerProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vehicle_jobs',
    )
    assigned_workers_snapshot = models.JSONField(default=list, blank=True)
    worker_payment_type = models.CharField(
        max_length=20,
        choices=WorkerPaymentType.choices,
        default=WorkerPaymentType.PERCENT,
    )
    worker_payment_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    worker_payment_fixed = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    service_list_subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    services_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    products_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    facility_discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    apply_loyalty_discount = models.BooleanField(default=True)
    loyalty_discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    manual_discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    facility_discount_locked = models.BooleanField(default=True)
    tax_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    final_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    worker_share_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    workers_tip_share_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    carwash_share_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tip_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    worker_share_paid_at = models.DateTimeField(null=True, blank=True)
    tip_paid_at = models.DateTimeField(null=True, blank=True)
    delivered_to_worker_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-id']


class VehicleJobService(models.Model):
    tenant = models.ForeignKey(
        'cw_auth.CarWash',
        on_delete=models.CASCADE,
        related_name='vehicle_job_services',
        null=True,
        blank=True,
    )
    vehicle_job = models.ForeignKey(
        VehicleJob, on_delete=models.CASCADE, related_name='service_lines'
    )
    service = models.ForeignKey(
        'services.Service',
        on_delete=models.PROTECT,
        related_name='vehicle_job_lines',
        null=True,
        blank=True,
    )
    custom_service_name = models.CharField(max_length=120, blank=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=1)
    list_unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_completed = models.BooleanField(default=False)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['vehicle_job', 'service'], name='uniq_vehicle_job_service'
            )
        ]


class VehicleJobProduct(models.Model):
    tenant = models.ForeignKey(
        'cw_auth.CarWash',
        on_delete=models.CASCADE,
        related_name='vehicle_job_products',
        null=True,
        blank=True,
    )
    vehicle_job = models.ForeignKey(
        VehicleJob, on_delete=models.CASCADE, related_name='product_lines'
    )
    product = models.ForeignKey(
        'products.Product', on_delete=models.PROTECT, related_name='vehicle_job_lines'
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['vehicle_job', 'product'], name='uniq_vehicle_job_product'
            )
        ]
