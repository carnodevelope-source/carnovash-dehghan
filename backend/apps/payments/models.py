from django.conf import settings
from django.db import models


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Wallet(TimestampedModel):
    class WalletType(models.TextChoices):
        CASH = 'cash', 'Cash'
        POS = 'pos', 'POS'
        BANK = 'bank', 'Bank'
        SMS = 'sms', 'SMS'

    tenant = models.ForeignKey(
        'cw_auth.CarWash',
        on_delete=models.CASCADE,
        related_name='wallets',
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=120)
    wallet_type = models.CharField(max_length=20, choices=WalletType.choices)
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class Payment(TimestampedModel):
    class Method(models.TextChoices):
        POS = 'pos', 'POS'
        CASH = 'cash', 'Cash'
        TRANSFER = 'transfer', 'Transfer'
        CHEQUE = 'cheque', 'Cheque'
        CREDIT = 'credit', 'Credit'
        MANUAL = 'manual', 'Manual'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'

    tenant = models.ForeignKey(
        'cw_auth.CarWash',
        on_delete=models.CASCADE,
        related_name='payments',
        null=True,
        blank=True,
    )
    vehicle_entry = models.ForeignKey(
        'vehicles.VehicleEntry', on_delete=models.CASCADE, related_name='payments'
    )
    method = models.CharField(max_length=20, choices=Method.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    tip_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    service_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    product_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pos_reference = models.CharField(max_length=100, blank=True)
    rrn = models.CharField(max_length=60, blank=True)
    gateway_payload = models.JSONField(default=dict, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    wallet = models.ForeignKey(
        Wallet, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments'
    )
    payer_name = models.CharField(max_length=120, blank=True)
    payer_phone = models.CharField(max_length=20, blank=True)
    cheque_number = models.CharField(max_length=60, blank=True)
    cheque_serial_number = models.CharField(max_length=80, blank=True)
    cheque_sayadi_number = models.CharField(max_length=80, blank=True)
    cheque_bank = models.CharField(max_length=120, blank=True)
    cheque_shaba = models.CharField(max_length=40, blank=True)
    cheque_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reminder_due_at = models.DateTimeField(null=True, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments_created',
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['status', 'method', 'created_at'])]


class CashflowTransaction(TimestampedModel):
    class Direction(models.TextChoices):
        IN = 'in', 'In'
        OUT = 'out', 'Out'

    tenant = models.ForeignKey(
        'cw_auth.CarWash',
        on_delete=models.CASCADE,
        related_name='cashflow_transactions',
        null=True,
        blank=True,
    )
    wallet = models.ForeignKey(
        Wallet, on_delete=models.CASCADE, related_name='cashflow_transactions'
    )
    direction = models.CharField(max_length=10, choices=Direction.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    reference_type = models.CharField(max_length=40, blank=True)
    reference_id = models.PositiveBigIntegerField(null=True, blank=True)
    transacted_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cashflow_transactions_created',
    )

    class Meta:
        ordering = ['-transacted_at']
        indexes = [models.Index(fields=['wallet', 'transacted_at'])]


class WalletGatewayRequest(TimestampedModel):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        CANCELLED = 'cancelled', 'Cancelled'
        EXPIRED = 'expired', 'Expired'

    tenant = models.ForeignKey(
        'cw_auth.CarWash',
        on_delete=models.CASCADE,
        related_name='wallet_gateway_requests',
        null=True,
        blank=True,
    )
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='gateway_requests',
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='wallet_gateway_requests_created',
    )

    class Meta:
        ordering = ['-created_at']
