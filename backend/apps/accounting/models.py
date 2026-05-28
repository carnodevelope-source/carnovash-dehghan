from django.conf import settings
from django.db import models


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Account(TimestampedModel):
    class Nature(models.TextChoices):
        ASSET = 'asset', 'Asset'
        LIABILITY = 'liability', 'Liability'
        EQUITY = 'equity', 'Equity'
        REVENUE = 'revenue', 'Revenue'
        EXPENSE = 'expense', 'Expense'

    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=120)
    nature = models.CharField(max_length=20, choices=Nature.choices)
    is_active = models.BooleanField(default=True)
    parent = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children'
    )

    class Meta:
        ordering = ['code']

    def __str__(self) -> str:
        return f'{self.code} - {self.name}'


class Party(TimestampedModel):
    class PartyType(models.TextChoices):
        SUPPLIER = 'supplier', 'Supplier'
        CUSTOMER = 'customer', 'Customer'
        BOTH = 'both', 'Both'

    name = models.CharField(max_length=150)
    mobile = models.CharField(max_length=20, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    national_id = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    party_type = models.CharField(max_length=20, choices=PartyType.choices, default=PartyType.BOTH)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class JournalEntry(TimestampedModel):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        POSTED = 'posted', 'Posted'

    voucher_no = models.CharField(max_length=60, unique=True)
    reference_type = models.CharField(max_length=40, blank=True)
    reference_id = models.PositiveBigIntegerField(null=True, blank=True)
    entry_date = models.DateField()
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='journal_entries_created',
    )

    class Meta:
        ordering = ['-entry_date', '-id']
        indexes = [models.Index(fields=['status', 'entry_date'])]


class JournalEntryLine(models.Model):
    journal_entry = models.ForeignKey(
        JournalEntry, on_delete=models.CASCADE, related_name='lines'
    )
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='entry_lines')
    description = models.CharField(max_length=255, blank=True)
    debit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        indexes = [models.Index(fields=['account'])]


class PurchaseInvoice(TimestampedModel):
    class PaymentType(models.TextChoices):
        CASH = 'cash', 'Cash'
        BANK = 'bank', 'Bank'
        MIXED = 'mixed', 'Mixed'
        CREDIT = 'credit', 'Credit'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        CONFIRMED = 'confirmed', 'Confirmed'
        CANCELLED = 'cancelled', 'Cancelled'

    class PaymentStatus(models.TextChoices):
        UNPAID = 'unpaid', 'Unpaid'
        PAID = 'paid', 'Paid'
        PARTIAL = 'partial', 'Partial'
        CREDIT = 'credit', 'Credit'

    invoice_no = models.CharField(max_length=60, unique=True)
    supplier = models.ForeignKey(
        Party, on_delete=models.PROTECT, related_name='purchase_invoices', null=True, blank=True
    )
    invoice_date = models.DateField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    total_discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_type = models.CharField(max_length=20, choices=PaymentType.choices, default=PaymentType.CASH)
    remaining_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchase_invoices_created',
    )

    class Meta:
        ordering = ['-invoice_date', '-id']


class PurchaseInvoiceLine(models.Model):
    purchase_invoice = models.ForeignKey(
        PurchaseInvoice, on_delete=models.CASCADE, related_name='lines'
    )
    product = models.ForeignKey(
        'products.Product', on_delete=models.PROTECT, related_name='purchase_lines'
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)


class SalesInvoice(TimestampedModel):
    class SettlementType(models.TextChoices):
        CASH = 'cash', 'Cash'
        CARD = 'card', 'Card'
        CREDIT = 'credit', 'Credit'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        CONFIRMED = 'confirmed', 'Confirmed'
        CANCELLED = 'cancelled', 'Cancelled'

    class PaymentStatus(models.TextChoices):
        UNPAID = 'unpaid', 'Unpaid'
        PAID = 'paid', 'Paid'
        PARTIAL = 'partial', 'Partial'
        REFUNDED = 'refunded', 'Refunded'

    vehicle_entry = models.OneToOneField(
        'vehicles.VehicleEntry',
        on_delete=models.CASCADE,
        related_name='sales_invoice',
        null=True,
        blank=True,
    )
    invoice_no = models.CharField(max_length=60, unique=True)
    invoice_date = models.DateField()
    customer = models.ForeignKey(
        Party, on_delete=models.PROTECT, related_name='sales_invoices', null=True, blank=True
    )
    description = models.TextField(blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_status = models.CharField(
        max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID
    )
    settlement_type = models.CharField(
        max_length=20, choices=SettlementType.choices, default=SettlementType.CASH
    )
    remaining_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales_invoices_created',
    )

    class Meta:
        ordering = ['-invoice_date', '-id']


class SalesInvoiceLine(models.Model):
    class LineType(models.TextChoices):
        SERVICE = 'service', 'Service'
        PRODUCT = 'product', 'Product'

    sales_invoice = models.ForeignKey(
        SalesInvoice, on_delete=models.CASCADE, related_name='lines'
    )
    line_type = models.CharField(max_length=20, choices=LineType.choices)
    service = models.ForeignKey(
        'services.Service',
        on_delete=models.PROTECT,
        related_name='sales_lines',
        null=True,
        blank=True,
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT,
        related_name='sales_lines',
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=150)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    description = models.CharField(max_length=255, blank=True)
