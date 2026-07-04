from django.conf import settings
from django.db import models


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


DEFAULT_SMS_VEHICLE_ASSIGNED_TEMPLATE = (
    '[خطاب مشتری]\n'
    'خودروی شما با پلاک [پلاک] در ساعت [ساعت تخصیص] روز [تاریخ تخصیص] در کارواش [نام کارواش] '
    'برای انجام خدمات ثبت و تخصیص داده شد.'
)

DEFAULT_SMS_VEHICLE_ASSIGNED_INVOICE_TEMPLATE = (
    'پیش فاکتور خدمات:\n'
    '[خلاصه خدمات]\n'
    'جمع کل: [جمع کل]\n'
    'خودروی شما حدود 1 ساعت کاری دیگر آماده ترخیص است.\n'
    'از اعتماد شما سپاسگزاریم 🌿'
)

DEFAULT_SMS_VEHICLE_RELEASED_TEMPLATE = (
    '[خطاب مشتری]\n'
    'خودروی شما در ساعت [ساعت ترخیص] روز [تاریخ ترخیص] از کارواش [نام کارواش] ترخیص شد.\n'
    'امتیاز شما: [امتیاز مشتری] از ۵\n'
    'درصد تخفیف سفارش بعد: [درصد تخفیف سفارش بعد]\n'
    'مبلغ نهایی: [مبلغ نهایی]\n'
    'جمع تخفیف: [جمع تخفیف]\n'
    '[نام کارواش]'
)


class ServiceCategory(TimestampedModel):
    tenant = models.ForeignKey(
        'cw_auth.CarWash',
        on_delete=models.CASCADE,
        related_name='service_categories',
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_categories_created',
    )

    class Meta:
        ordering = ['display_order', 'name']

    def __str__(self) -> str:
        return self.name


class Service(TimestampedModel):
    class PricingMode(models.TextChoices):
        FIXED = 'fixed', 'Fixed'
        VARIABLE = 'variable', 'Variable'

    tenant = models.ForeignKey(
        'cw_auth.CarWash',
        on_delete=models.CASCADE,
        related_name='services',
        null=True,
        blank=True,
    )
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='services',
    )
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=30, unique=True, null=True, blank=True)
    description = models.TextField(blank=True)
    base_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pricing_mode = models.CharField(
        max_length=20, choices=PricingMode.choices, default=PricingMode.FIXED
    )
    estimated_duration_minutes = models.PositiveIntegerField(default=30)
    allow_price_override = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='services_created',
    )

    class Meta:
        ordering = ['display_order', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['category', 'name'], name='uniq_service_name_per_category'
            )
        ]

    def __str__(self) -> str:
        return self.name


class ServiceChangeLog(TimestampedModel):
    class ActionType(models.TextChoices):
        CREATED = 'created', 'Created'
        UPDATED = 'updated', 'Updated'
        DEACTIVATED = 'deactivated', 'Deactivated'
        DELETED = 'deleted', 'Deleted'

    tenant = models.ForeignKey(
        'cw_auth.CarWash',
        on_delete=models.CASCADE,
        related_name='service_change_logs',
        null=True,
        blank=True,
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='change_logs',
    )
    action_type = models.CharField(max_length=20, choices=ActionType.choices, default=ActionType.UPDATED)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_change_logs_created',
    )
    name_snapshot = models.CharField(max_length=120)
    base_price_snapshot = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estimated_duration_snapshot = models.PositiveIntegerField(default=30)
    is_active_snapshot = models.BooleanField(default=True)
    change_summary = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class GeneralSettings(TimestampedModel):
    tenant = models.OneToOneField(
        'cw_auth.CarWash',
        on_delete=models.CASCADE,
        related_name='general_settings',
        null=True,
        blank=True,
    )
    discount_percent_per_half_star = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    preferred_bank_name = models.CharField(max_length=120, blank=True)
    bank_account_holder = models.CharField(max_length=120, blank=True)
    bank_card_number = models.CharField(max_length=32, blank=True)
    bank_account_iban = models.CharField(max_length=40, blank=True)
    pos_device_name = models.CharField(max_length=120, blank=True)
    pos_terminal_id = models.CharField(max_length=80, blank=True)
    payment_methods_note = models.TextField(blank=True)
    receipt_printer_enabled = models.BooleanField(default=False)
    receipt_printer_name = models.CharField(max_length=120, blank=True)
    receipt_printer_paper_width = models.CharField(max_length=20, blank=True, default='80mm')
    receipt_print_copies = models.PositiveSmallIntegerField(default=1)
    receipt_auto_print = models.BooleanField(default=False)
    receipt_show_logo = models.BooleanField(default=False)
    receipt_show_qr = models.BooleanField(default=False)
    receipt_footer_note = models.TextField(blank=True)
    sms_provider_base_url = models.CharField(max_length=255, blank=True, default='https://api.iranpayamak.com')
    sms_provider_api_key = models.CharField(max_length=255, blank=True)
    sms_provider_line_number = models.CharField(max_length=50, blank=True)
    sms_vehicle_assigned_template = models.TextField(blank=True, default=DEFAULT_SMS_VEHICLE_ASSIGNED_TEMPLATE)
    sms_vehicle_assigned_invoice_template = models.TextField(blank=True, default=DEFAULT_SMS_VEHICLE_ASSIGNED_INVOICE_TEMPLATE)
    sms_vehicle_released_template = models.TextField(blank=True, default=DEFAULT_SMS_VEHICLE_RELEASED_TEMPLATE)

    class Meta:
        verbose_name = 'General Settings'
        verbose_name_plural = 'General Settings'

    def __str__(self) -> str:
        return 'General Settings'
