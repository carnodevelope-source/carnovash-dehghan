from django.conf import settings
from django.db import models
from django.utils import timezone


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class InventoryItem(TimestampedModel):
    tenant = models.ForeignKey(
        'cw_auth.CarWash',
        on_delete=models.CASCADE,
        related_name='inventory_items',
        null=True,
        blank=True,
    )
    product = models.OneToOneField(
        'products.Product', on_delete=models.CASCADE, related_name='inventory_item'
    )
    quantity_on_hand = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reserved_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    min_quantity_alert = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    location = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ['product__name']

    @property
    def available_quantity(self):
        return self.quantity_on_hand - self.reserved_quantity


class StockMovement(TimestampedModel):
    class MovementType(models.TextChoices):
        IN = 'in', 'In'
        OUT = 'out', 'Out'
        ADJUSTMENT = 'adjustment', 'Adjustment'

    tenant = models.ForeignKey(
        'cw_auth.CarWash',
        on_delete=models.CASCADE,
        related_name='stock_movements',
        null=True,
        blank=True,
    )
    inventory_item = models.ForeignKey(
        InventoryItem, on_delete=models.CASCADE, related_name='movements'
    )
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sale_price_snapshot = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    note = models.TextField(blank=True)
    reference_type = models.CharField(max_length=40, blank=True)
    reference_id = models.PositiveBigIntegerField(null=True, blank=True)
    moved_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements_created',
    )

    class Meta:
        ordering = ['-moved_at']
        indexes = [
            models.Index(fields=['movement_type', 'moved_at']),
            models.Index(fields=['reference_type', 'reference_id']),
        ]


class ExpenseEntry(TimestampedModel):
    class SourceType(models.TextChoices):
        MANUAL = 'manual', 'Manual'

    tenant = models.ForeignKey(
        'cw_auth.CarWash',
        on_delete=models.CASCADE,
        related_name='expense_entries',
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=180)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    details = models.TextField(blank=True)
    attachment = models.FileField(upload_to='expenses/%Y/%m/', null=True, blank=True)
    attachment_original_name = models.CharField(max_length=255, blank=True)
    source_type = models.CharField(max_length=20, choices=SourceType.choices, default=SourceType.MANUAL)
    spent_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expense_entries_created',
    )

    class Meta:
        ordering = ['-spent_at', '-id']
        indexes = [
            models.Index(fields=['source_type', 'spent_at']),
        ]
