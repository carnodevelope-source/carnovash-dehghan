from django.contrib.auth.models import AbstractUser
from django.db import models


class CarWash(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    address = models.CharField(max_length=300, blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


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
        max_length=20,
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

    REQUIRED_FIELDS = ['email', 'phone']

    def __str__(self) -> str:
        return self.username


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
