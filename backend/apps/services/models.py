from django.conf import settings
from django.db import models


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ServiceCategory(TimestampedModel):
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
