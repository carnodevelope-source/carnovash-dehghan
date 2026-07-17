from django.conf import settings
from django.db import models


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


DEFAULT_SMS_VEHICLE_ASSIGNED_TEMPLATE = (
    '[نام مشتری] عزیز\n'
    'شماره پذیرش: [شماره پذیرش]\n'
    'خودروی شما با پلاک [پلاک]، در ساعت [ساعت تخصیص]، روز [تاریخ تخصیص] در مجموعه کارواش [نام کارواش] '
    'برای انجام خدمات، پذیرش شد.\n\n'
    'پیش فاکتور خدمات:\n'
    '[خلاصه خدمات]\n'
    'جمع کل: [جمع کل]\n'
    'تخفیف این سفارش: [جمع تخفیف]\n'
    'مبلغ نهایی بعد از تخفیف: [مبلغ نهایی]\n'
    'خودروی شما حدود 30 دقیقه دیگر آماده ترخیص است.\n'
    'از اعتماد شما سپاسگزاریم.'
)
DEFAULT_SMS_VEHICLE_ASSIGNED_INVOICE_TEMPLATE = ''

DEFAULT_SMS_VEHICLE_RELEASED_TEMPLATE = (
    '[نام مشتری] عزیز\n'
    'خودروی شما در ساعت [ساعت ترخیص] روز [تاریخ ترخیص] از مجموعه کارواش [نام کارواش] ترخیص شد.\n'
    'امتیاز شما: [امتیاز مشتری] از ۵\n'
    'درصد تخفیف مراجعه بعد: [درصد تخفیف مراجعه بعد]\n'
    'تعداد دفعات مراجعه: [تعداد مراجعات]\n'
    'انعام: [انعام]\n'
    'جمع تخفیف: [جمع تخفیف]\n'
    'مبلغ نهایی: [مبلغ نهایی]\n'
    'به امید دیدار مجدد'
)


def normalize_vehicle_assigned_sms_template(template):
    text = str(template or '').strip()
    if not text:
        return DEFAULT_SMS_VEHICLE_ASSIGNED_TEMPLATE
    text = text.replace('[خطاب مشتری]', '[نام مشتری] عزیز')
    replacements = {
        'با پلاک [پلاک] در ساعت': 'با پلاک [پلاک]، در ساعت',
        '[ساعت تخصیص] روز': '[ساعت تخصیص]، روز',
        '[تاریخ تخصیص]، در کارواش': '[تاریخ تخصیص] در مجموعه کارواش',
        '[تاریخ تخصیص] در کارواش': '[تاریخ تخصیص] در مجموعه کارواش',
        'برای انجام خدمات ثبت و تخصیص داده شد': 'برای انجام خدمات، پذیرش شد',
        'برای انجام خدمات، ثبت و تخصیص داده شد': 'برای انجام خدمات، پذیرش شد',
        'تخصیص داده شد': 'پذیرش شد',
        '1 ساعت کاری': '30 دقیقه',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    if '[شماره پذیرش]' not in text:
        lines = text.splitlines()
        lines.insert(1 if lines else 0, 'شماره پذیرش: [شماره پذیرش]')
        text = '\n'.join(lines)
    return text


def normalize_vehicle_released_sms_template(template):
    text = (
        str(template or '')
        .replace('[خطاب مشتری]', '[نام مشتری] عزیز')
        .replace('سفارش بعد', 'مراجعه بعد')
        .replace('از کارواش', 'از مجموعه کارواش')
        .strip()
    )
    if not text:
        return DEFAULT_SMS_VEHICLE_RELEASED_TEMPLATE

    lines = text.splitlines()
    insertions = []
    if '[تعداد مراجعات]' not in text:
        insertions.append('تعداد دفعات مراجعه: [تعداد مراجعات]')
    if '[انعام]' not in text:
        insertions.append('انعام: [انعام]')
    if not insertions:
        return text

    anchor_index = next(
        (index for index, line in enumerate(lines) if '[درصد تخفیف سفارش بعد]' in line or '[درصد تخفیف مراجعه بعد]' in line),
        -1,
    )
    insert_at = anchor_index + 1 if anchor_index >= 0 else max(1, len(lines) - 3)
    lines[insert_at:insert_at] = insertions
    return '\n'.join(lines)


CAR_SERVICE_TIER_KEYS = ('type_1', 'type_2', 'type_3', 'type_4')
MOTORCYCLE_SERVICE_TIER_KEYS = ('type_1', 'type_2')


def default_service_tiers(keys, *, sale_price=0, duration_minutes=30):
    normalized_price = float(sale_price or 0)
    normalized_duration = int(duration_minutes or 0) or 30
    return {
        key: {
            'list_price': normalized_price,
            'sale_price': normalized_price,
            'duration_minutes': normalized_duration,
        }
        for key in keys
    }


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
    pricing_tiers = models.JSONField(default=dict, blank=True)
    motorcycle_enabled = models.BooleanField(default=False)
    motorcycle_pricing_tiers = models.JSONField(default=dict, blank=True)
    allow_price_override = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='services_deleted',
    )
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

    def normalized_pricing_tiers(self, *, plate_type='car'):
        keys = MOTORCYCLE_SERVICE_TIER_KEYS if plate_type == 'motorcycle' else CAR_SERVICE_TIER_KEYS
        source = self.motorcycle_pricing_tiers if plate_type == 'motorcycle' else self.pricing_tiers
        defaults = default_service_tiers(
            keys,
            sale_price=self.base_price,
            duration_minutes=self.estimated_duration_minutes,
        )
        if not isinstance(source, dict):
            return defaults

        normalized = {}
        for key in keys:
            raw_item = source.get(key, {}) if isinstance(source.get(key, {}), dict) else {}
            normalized[key] = {
                'list_price': float(raw_item.get('list_price', defaults[key]['list_price']) or 0),
                'sale_price': float(raw_item.get('sale_price', defaults[key]['sale_price']) or 0),
                'duration_minutes': int(raw_item.get('duration_minutes', defaults[key]['duration_minutes']) or defaults[key]['duration_minutes']),
            }
        return normalized

    def resolve_pricing(self, *, tariff_type='type_1', plate_type='car'):
        normalized_plate_type = 'motorcycle' if plate_type == 'motorcycle' else 'car'
        tiers = self.normalized_pricing_tiers(plate_type=normalized_plate_type)
        fallback_key = MOTORCYCLE_SERVICE_TIER_KEYS[0] if normalized_plate_type == 'motorcycle' else CAR_SERVICE_TIER_KEYS[0]
        tier_key = str(tariff_type or fallback_key).strip().lower() or fallback_key
        if tier_key not in tiers:
            tier_key = fallback_key
        tier = tiers[tier_key]
        return {
            'tariff_type': tier_key,
            'list_price': tier['list_price'],
            'sale_price': tier['sale_price'],
            'duration_minutes': tier['duration_minutes'],
        }


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
    tax_enabled = models.BooleanField(default=False)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
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
    sms_vehicle_auto_send_enabled = models.BooleanField(default=True)
    sms_vehicle_assigned_template = models.TextField(blank=True, default=DEFAULT_SMS_VEHICLE_ASSIGNED_TEMPLATE)
    sms_vehicle_assigned_invoice_template = models.TextField(blank=True, default=DEFAULT_SMS_VEHICLE_ASSIGNED_INVOICE_TEMPLATE)
    sms_vehicle_released_template = models.TextField(blank=True, default=DEFAULT_SMS_VEHICLE_RELEASED_TEMPLATE)

    class Meta:
        verbose_name = 'General Settings'
        verbose_name_plural = 'General Settings'

    def __str__(self) -> str:
        return 'General Settings'
