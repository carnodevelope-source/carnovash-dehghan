from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.realtime.transactions import TransactionalLiveModelMixin


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class PlatformProject(TimestampedModel):
    """Logical product line (کارنواش / کارنومند / ...)."""

    code = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=100)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class ServiceProduct(TimestampedModel):
    class ProductKey(models.TextChoices):
        CORE_SOFTWARE = 'core_software', 'لایسنس اصلی نرم‌افزار'
        WALLET = 'wallet', 'کیف پول'
        ATTENDANCE = 'attendance', 'ورود و خروج'
        CLOUD_STORAGE = 'cloud_storage', 'فضای ابری'
        SMS_CLUB = 'sms_club', 'پنل پیشرفته مشتریان'
        SMS_PANEL = 'sms_panel', 'پنل پیامک'
        SMS_CREDIT = 'sms_credit', 'بسته و اعتبار پیامک'
        ACCOUNTING = 'accounting', 'حسابداری'
        EXCEL_IMPORT = 'excel_import', 'ورود اکسل'
        CUSTOM_ADDON = 'custom_addon', 'افزونه اختصاصی'

    project = models.ForeignKey(
        PlatformProject,
        on_delete=models.PROTECT,
        related_name='products',
    )
    product_key = models.CharField(max_length=50, choices=ProductKey.choices, db_index=True)
    feature_key = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text='Maps to CarWashFeaturePurchase.feature_key when gating is required.',
    )
    title = models.CharField(max_length=150)
    subtitle = models.CharField(max_length=200, blank=True, default='')
    description = models.TextField(blank=True, default='')
    features_json = models.JSONField(default=list, blank=True)
    limits_json = models.JSONField(default=dict, blank=True)
    is_available = models.BooleanField(default=True)
    is_required = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=100)
    default_cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('10'))
    grace_days_default = models.PositiveSmallIntegerField(default=7)
    reminder_days_json = models.JSONField(default=list, blank=True)
    accent = models.CharField(max_length=20, blank=True, default='#0f172a')

    class Meta:
        ordering = ['sort_order', 'title']
        constraints = [
            models.UniqueConstraint(fields=['project', 'product_key'], name='uniq_service_product_per_project'),
        ]
        indexes = [
            models.Index(fields=['product_key', 'is_available']),
        ]

    def __str__(self):
        return f'{self.project.code}:{self.title}'


class ServicePlan(TimestampedModel):
    class BillingCycle(models.TextChoices):
        MONTHLY = 'monthly', 'ماهانه'
        QUARTERLY = 'quarterly', 'سه‌ماهه'
        SEMIANNUAL = 'semiannual', 'شش‌ماهه'
        ANNUAL = 'annual', 'سالانه'
        PERPETUAL = 'perpetual', 'دائمی'
        USAGE = 'usage', 'مصرفی'
        CUSTOM = 'custom', 'اختصاصی'
        INSTALLMENT = 'installment', 'اقساطی'

    product = models.ForeignKey(ServiceProduct, on_delete=models.CASCADE, related_name='plans')
    code = models.SlugField(max_length=60)
    title = models.CharField(max_length=120)
    billing_cycle = models.CharField(max_length=20, choices=BillingCycle.choices)
    duration_days = models.PositiveIntegerField(default=0, help_text='0 means perpetual/usage')
    base_price = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0'))
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    usage_cap = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    usage_unit = models.CharField(max_length=40, blank=True, default='')
    enabled_features_json = models.JSONField(default=list, blank=True)
    disabled_features_json = models.JSONField(default=list, blank=True)
    renewal_terms = models.TextField(blank=True, default='')
    installment_months = models.PositiveSmallIntegerField(default=0)
    upfront_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    monthly_installment_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=100)

    class Meta:
        ordering = ['sort_order', 'title']
        constraints = [
            models.UniqueConstraint(fields=['product', 'code'], name='uniq_service_plan_code'),
        ]

    def __str__(self):
        return f'{self.product.product_key}:{self.code}'

    def compute_amounts(self, discount_override=None):
        tax_percent = self.tax_percent if self.tax_percent is not None else self.product.tax_percent
        discount_percent = discount_override if discount_override is not None else self.discount_percent
        base = Decimal(self.base_price or 0)
        discount = (base * Decimal(discount_percent or 0) / Decimal('100')).quantize(Decimal('0.01'))
        taxable = max(Decimal('0'), base - discount)
        tax = (taxable * Decimal(tax_percent or 0) / Decimal('100')).quantize(Decimal('0.01'))
        final = taxable + tax
        return {
            'base_amount': base,
            'discount_amount': discount,
            'tax_amount': tax,
            'final_amount': final,
            'tax_percent': Decimal(tax_percent or 0),
            'discount_percent': Decimal(discount_percent or 0),
        }


class ServiceSubscription(TransactionalLiveModelMixin, TimestampedModel):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'فعال'
        INACTIVE = 'inactive', 'غیرفعال'
        EXPIRED = 'expired', 'منقضی'
        NEAR_EXPIRY = 'near_expiry', 'نزدیک انقضا'
        BLOCKED = 'blocked', 'مسدود'
        SUSPENDED = 'suspended', 'تعلیقشده'
        PENDING_PAYMENT = 'pending_payment', 'در انتظار پرداخت'
        PENDING_ACTIVATION = 'pending_activation', 'در انتظار فعالسازی'
        CANCELLED = 'cancelled', 'لغوشده'
        TRIAL = 'trial', 'آزمایشی'
        NOT_RENEWED = 'not_renewed', 'تمدیدنشده'

    class PaymentStatus(models.TextChoices):
        SETTLED = 'settled', 'تسویهشده'
        PARTIAL = 'partial', 'پرداخت جزئی'
        UNPAID = 'unpaid', 'پرداختنشده'
        OVERDUE = 'overdue', 'معوق'
        EARLY = 'early', 'پرداخت زودتر از موعد'

    tenant = models.ForeignKey(
        'cw_auth.CarWash',
        on_delete=models.CASCADE,
        related_name='service_subscriptions',
    )
    project = models.ForeignKey(PlatformProject, on_delete=models.PROTECT, related_name='subscriptions')
    product = models.ForeignKey(ServiceProduct, on_delete=models.PROTECT, related_name='subscriptions')
    plan = models.ForeignKey(ServicePlan, on_delete=models.PROTECT, related_name='subscriptions', null=True, blank=True)
    feature_purchase = models.ForeignKey(
        'cw_auth.CarWashFeaturePurchase',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subscriptions',
    )
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING_PAYMENT, db_index=True)
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
        db_index=True,
    )
    auto_renew = models.BooleanField(default=False)
    purchased_at = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    grace_ends_at = models.DateTimeField(null=True, blank=True)
    last_renewed_at = models.DateTimeField(null=True, blank=True)
    last_paid_at = models.DateTimeField(null=True, blank=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)
    base_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    final_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    remaining_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    cost_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    usage_cap = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    usage_used = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    usage_unit = models.CharField(max_length=40, blank=True, default='')
    license_code = models.CharField(max_length=80, blank=True, default='')
    seat_limit = models.PositiveIntegerField(default=0)
    device_limit = models.PositiveIntegerField(default=0)
    sales_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales_owned_subscriptions',
    )
    support_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='support_owned_subscriptions',
    )
    contract_number = models.CharField(max_length=80, blank=True, default='')
    meta = models.JSONField(default=dict, blank=True)
    idempotency_key = models.CharField(max_length=64, blank=True, default='', db_index=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['product', 'status']),
            models.Index(fields=['ends_at', 'status']),
            models.Index(fields=['payment_status']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'product'],
                name='uniq_active_subscription_per_tenant_product',
            ),
        ]

    def __str__(self):
        return f'{self.tenant_id}:{self.product.product_key}:{self.status}'

    @property
    def days_remaining(self):
        if not self.ends_at:
            return None
        delta = self.ends_at.date() - timezone.localdate()
        return delta.days

    @property
    def usage_percent(self):
        if not self.usage_cap or self.usage_cap <= 0:
            return Decimal('0')
        return (Decimal(self.usage_used or 0) * Decimal('100') / Decimal(self.usage_cap)).quantize(Decimal('0.01'))


class ServicePeriod(TimestampedModel):
    """Append-only history of purchase/renewal periods (never overwrite)."""

    class Kind(models.TextChoices):
        PURCHASE = 'purchase', 'خرید'
        RENEWAL = 'renewal', 'تمدید'
        TRIAL = 'trial', 'آزمایشی'
        MANUAL = 'manual', 'دستی'
        PLAN_CHANGE = 'plan_change', 'تغییر پلن'

    subscription = models.ForeignKey(ServiceSubscription, on_delete=models.CASCADE, related_name='periods')
    plan = models.ForeignKey(ServicePlan, on_delete=models.PROTECT, related_name='periods', null=True, blank=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.PURCHASE)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    base_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    final_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    cost_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    note = models.CharField(max_length=255, blank=True, default='')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_periods_created',
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['subscription', 'starts_at'])]


class ServiceOrder(TransactionalLiveModelMixin, TimestampedModel):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'پیش‌نویس'
        PENDING_PAYMENT = 'pending_payment', 'در انتظار پرداخت'
        PENDING_APPROVAL = 'pending_approval', 'در انتظار تأیید'
        PAID = 'paid', 'پرداخت‌شده'
        ACTIVATED = 'activated', 'فعال‌شده'
        REJECTED = 'rejected', 'ردشده'
        CANCELLED = 'cancelled', 'لغوشده'

    class PaymentMethod(models.TextChoices):
        WALLET = 'wallet', 'کیف پول'
        GATEWAY = 'gateway', 'اینترنتی'
        TRANSFER = 'transfer', 'کارت‌به‌کارت'
        CREDIT = 'credit', 'اعتباری'
        INSTALLMENT = 'installment', 'اقساطی'
        MANUAL_HQ = 'manual_hq', 'ثبت دستی HQ'

    order_code = models.CharField(max_length=40, unique=True, db_index=True)
    tenant = models.ForeignKey('cw_auth.CarWash', on_delete=models.CASCADE, related_name='service_orders')
    project = models.ForeignKey(PlatformProject, on_delete=models.PROTECT, related_name='orders')
    product = models.ForeignKey(ServiceProduct, on_delete=models.PROTECT, related_name='orders')
    plan = models.ForeignKey(ServicePlan, on_delete=models.PROTECT, related_name='orders', null=True, blank=True)
    subscription = models.ForeignKey(
        ServiceSubscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
    )
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING_PAYMENT, db_index=True)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.WALLET)
    base_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    final_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    remaining_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    tracking_code = models.CharField(max_length=80, blank=True, default='')
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_orders_approved',
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=64, blank=True, default='', db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_orders_created',
    )
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['product', 'status']),
        ]


class ServicePaymentRecord(TransactionalLiveModelMixin, TimestampedModel):
    class Kind(models.TextChoices):
        PURCHASE = 'purchase', 'خرید'
        RENEWAL = 'renewal', 'تمدید'
        INSTALLMENT = 'installment', 'قسط'
        MANUAL = 'manual', 'دستی'
        REFUND = 'refund', 'بازگشت'
        ADJUSTMENT = 'adjustment', 'اصلاح'

    order = models.ForeignKey(ServiceOrder, on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    subscription = models.ForeignKey(
        ServiceSubscription,
        on_delete=models.CASCADE,
        related_name='payments',
        null=True,
        blank=True,
    )
    period = models.ForeignKey(ServicePeriod, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    tenant = models.ForeignKey('cw_auth.CarWash', on_delete=models.CASCADE, related_name='service_payments')
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.PURCHASE)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    method = models.CharField(max_length=20, blank=True, default='')
    tracking_code = models.CharField(max_length=80, blank=True, default='')
    cashflow = models.ForeignKey(
        'payments.CashflowTransaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_payments',
    )
    paid_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_payments_created',
    )
    note = models.CharField(max_length=255, blank=True, default='')
    idempotency_key = models.CharField(max_length=64, blank=True, default='', db_index=True)

    class Meta:
        ordering = ['-paid_at']
        indexes = [models.Index(fields=['tenant', 'paid_at'])]


class ServiceAuditLog(TimestampedModel):
    subscription = models.ForeignKey(
        ServiceSubscription,
        on_delete=models.CASCADE,
        related_name='audit_logs',
        null=True,
        blank=True,
    )
    order = models.ForeignKey(ServiceOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    tenant = models.ForeignKey('cw_auth.CarWash', on_delete=models.CASCADE, related_name='service_audit_logs')
    action = models.CharField(max_length=60, db_index=True)
    reason = models.CharField(max_length=255, blank=True, default='')
    note = models.TextField(blank=True, default='')
    before_status = models.CharField(max_length=30, blank=True, default='')
    after_status = models.CharField(max_length=30, blank=True, default='')
    financial_impact = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    access_impact = models.CharField(max_length=255, blank=True, default='')
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_audit_actions',
    )
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['tenant', 'action', 'created_at'])]


class ServiceUsageMeter(TimestampedModel):
    subscription = models.ForeignKey(ServiceSubscription, on_delete=models.CASCADE, related_name='usage_meters')
    metric_key = models.CharField(max_length=60, db_index=True)
    metric_label = models.CharField(max_length=120, blank=True, default='')
    value = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    unit = models.CharField(max_length=40, blank=True, default='')
    recorded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-recorded_at']
        indexes = [models.Index(fields=['subscription', 'metric_key', 'recorded_at'])]


class BulkServiceJob(TimestampedModel):
    class Status(models.TextChoices):
        PENDING = 'pending', 'در صف'
        RUNNING = 'running', 'در حال اجرا'
        COMPLETED = 'completed', 'تمام‌شده'
        FAILED = 'failed', 'ناموفق'

    class Action(models.TextChoices):
        SMS_RENEWAL = 'sms_renewal', 'پیامک تمدید'
        SMS_DEBT = 'sms_debt', 'پیامک بدهی'
        SMS_EXPIRY = 'sms_expiry', 'پیامک انقضا'
        ACTIVATE = 'activate', 'فعالسازی'
        DEACTIVATE = 'deactivate', 'غیرفعالسازی'
        RENEW = 'renew', 'تمدید گروهی'
        CHANGE_PLAN = 'change_plan', 'تغییر پلن'
        APPLY_DISCOUNT = 'apply_discount', 'اعمال تخفیف'
        ADD_CREDIT = 'add_credit', 'افزایش اعتبار'
        ADD_CLOUD = 'add_cloud', 'افزایش فضای ابری'
        EXPORT = 'export', 'خروجی'
        ASSIGN_SUPPORT = 'assign_support', 'تخصیص پشتیبان'
        CREATE_INVOICE = 'create_invoice', 'ایجاد فاکتور'

    action = models.CharField(max_length=40, choices=Action.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    payload = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bulk_service_jobs',
    )
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    success_count = models.PositiveIntegerField(default=0)
    failure_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']


class BulkServiceJobItem(TimestampedModel):
    class Status(models.TextChoices):
        PENDING = 'pending', 'در صف'
        SUCCESS = 'success', 'موفق'
        FAILED = 'failed', 'ناموفق'

    job = models.ForeignKey(BulkServiceJob, on_delete=models.CASCADE, related_name='items')
    subscription = models.ForeignKey(
        ServiceSubscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bulk_items',
    )
    tenant = models.ForeignKey('cw_auth.CarWash', on_delete=models.CASCADE, related_name='bulk_service_items')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    message = models.CharField(max_length=255, blank=True, default='')
    result = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['id']


class ServiceAlert(TimestampedModel):
    class Severity(models.TextChoices):
        INFO = 'info', 'اطلاع'
        WARNING = 'warning', 'هشدار'
        CRITICAL = 'critical', 'بحرانی'

    tenant = models.ForeignKey('cw_auth.CarWash', on_delete=models.CASCADE, related_name='service_alerts')
    subscription = models.ForeignKey(
        ServiceSubscription,
        on_delete=models.CASCADE,
        related_name='alerts',
        null=True,
        blank=True,
    )
    code = models.CharField(max_length=60, db_index=True)
    title = models.CharField(max_length=180)
    message = models.TextField(blank=True, default='')
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.WARNING)
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['is_resolved', 'severity', 'created_at'])]
