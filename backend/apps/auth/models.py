from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class CarWash(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    address = models.CharField(max_length=300, blank=True, default='')
    is_active = models.BooleanField(default=True)
    exclude_from_hq_reports = models.BooleanField(default=False)
    trial_started_at = models.DateTimeField(null=True, blank=True)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return self.name

    def active_feature_keys(self):
        return list(
            self.feature_purchases.filter(is_active=True)
            .order_by('feature_key')
            .values_list('feature_key', flat=True)
        )

    def has_feature(self, feature_key):
        if not feature_key:
            return False
        return self.feature_purchases.filter(feature_key=feature_key, is_active=True).exists()

    def is_trial_active(self, now=None):
        now = now or timezone.now()
        return bool(self.trial_started_at and self.trial_ends_at and self.trial_started_at <= now < self.trial_ends_at)


class User(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        OWNER = 'owner', 'Owner'
        MANAGER = 'manager', 'Manager'
        ACCOUNTANT = 'accountant', 'Accountant'
        OPERATOR = 'operator', 'Operator'
        WORKER = 'worker', 'Worker'

    class PlatformRoles(models.TextChoices):
        NONE = '', 'None'
        HQ_ADMIN = 'hq_admin', 'HQ Admin'
        HQ_PROJECT_MANAGER = 'hq_project_manager', 'HQ Project Manager'
        HQ_FINANCE = 'hq_finance', 'HQ Finance'
        HQ_SUPPORT = 'hq_support', 'HQ Support'

    full_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, unique=True)
    tenant = models.ForeignKey(
        CarWash,
        on_delete=models.PROTECT,
        related_name='users',
        null=True,
        blank=True,
    )
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.OPERATOR)
    platform_role = models.CharField(
        max_length=32,
        choices=PlatformRoles.choices,
        default=PlatformRoles.NONE,
        blank=True,
    )
    is_active_worker = models.BooleanField(default=True)
    support_star_rating = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    support_rating_count = models.PositiveIntegerField(default=0)
    support_customer_satisfaction_avg = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    support_response_quality_avg = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    support_first_response_minutes_avg = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    support_total_responses = models.PositiveIntegerField(default=0)
    support_resolved_tickets_count = models.PositiveIntegerField(default=0)
    support_last_scored_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deleted_users',
    )

    REQUIRED_FIELDS = ['email', 'phone']

    def __str__(self) -> str:
        return self.username


class CarWashFeaturePurchase(models.Model):
    class FeatureKey(models.TextChoices):
        CORE_SOFTWARE = 'core_software', 'Core Software'
        EXCEL_IMPORT = 'excel_import', 'Excel Import'
        ATTENDANCE = 'attendance', 'Attendance'
        SMS_CLUB = 'sms_club', 'SMS Club'
        ACCOUNTING = 'accounting', 'Accounting'
        CLOUD_STORAGE = 'cloud_storage', 'Cloud Storage'

    class PaymentPlan(models.TextChoices):
        MANUAL = 'manual', 'Manual'
        CASH = 'cash', 'Cash'
        INSTALLMENT = 'installment', 'Installment'

    tenant = models.ForeignKey(
        CarWash,
        on_delete=models.CASCADE,
        related_name='feature_purchases',
    )
    feature_key = models.CharField(max_length=50, choices=FeatureKey.choices)
    is_active = models.BooleanField(default=True)
    payment_plan = models.CharField(max_length=20, choices=PaymentPlan.choices, default=PaymentPlan.MANUAL)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    remaining_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    installment_months = models.PositiveSmallIntegerField(default=0)
    monthly_installment_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    next_installment_due_at = models.DateTimeField(null=True, blank=True)
    purchased_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['tenant_id', 'feature_key']
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'feature_key'], name='uniq_carwash_feature_purchase')
        ]

    def __str__(self) -> str:
        return f'{self.tenant.name} | {self.feature_key}'


class SupportTicket(models.Model):
    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        PENDING = 'pending', 'Pending'
        ANSWERED = 'answered', 'Answered'
        CLOSED = 'closed', 'Closed'

    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        URGENT = 'urgent', 'Urgent'

    class Category(models.TextChoices):
        TECHNICAL = 'technical', 'Technical'
        FINANCIAL = 'financial', 'Financial'
        OPERATIONS = 'operations', 'Operations'
        ACCOUNT = 'account', 'Account'
        OTHER = 'other', 'Other'

    tenant = models.ForeignKey(
        CarWash,
        on_delete=models.CASCADE,
        related_name='support_tickets',
    )
    created_by = models.ForeignKey(
        'cw_auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_support_tickets',
    )
    subject = models.CharField(max_length=180)
    message = models.TextField(blank=True)
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER,
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    response_text = models.TextField(blank=True)
    assigned_to = models.ForeignKey(
        'cw_auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_support_tickets',
    )
    responded_by = models.ForeignKey(
        'cw_auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='responded_support_tickets',
    )
    first_response_at = models.DateTimeField(null=True, blank=True)
    response_quality_score = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    customer_satisfaction = models.PositiveSmallIntegerField(null=True, blank=True)
    customer_feedback = models.TextField(blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_registration_request = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.tenant.name} | {self.subject}'


class SupportTicketMessage(models.Model):
    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    sender = models.ForeignKey(
        'cw_auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='support_ticket_messages',
    )
    body = models.TextField()
    is_internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self) -> str:
        return f'Ticket #{self.ticket_id} message'


class SupportTicketAttachment(models.Model):
    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name='attachments',
    )
    uploaded_by = models.ForeignKey(
        'cw_auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='support_ticket_attachments',
    )
    file = models.FileField(upload_to='support_tickets/%Y/%m/')
    original_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self) -> str:
        return f'Ticket #{self.ticket_id} attachment'


class PendingTenantRegistration(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    tenant = models.OneToOneField(
        CarWash,
        on_delete=models.CASCADE,
        related_name='pending_registration',
    )
    manager = models.ForeignKey(
        'cw_auth.User',
        on_delete=models.CASCADE,
        related_name='pending_tenant_registrations',
    )
    support_ticket = models.OneToOneField(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name='registration_request',
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    temp_password = models.CharField(max_length=128, blank=True, default='')
    reviewed_by = models.ForeignKey(
        'cw_auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_tenant_registrations',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self) -> str:
        return f'Pending registration | {self.tenant.name}'
