from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.live import publish_live_event
from apps.products.models import Product, ProductCategory


@receiver(post_save, sender=ProductCategory)
def publish_product_category_event(sender, instance: ProductCategory, created: bool, **kwargs) -> None:
    publish_live_event(
        'product.category.created' if created else 'product.category.updated',
        {
            'id': instance.pk,
            'created': created,
            'tenant_id': instance.tenant_id,
            'is_active': instance.is_active,
        },
    )


@receiver(post_save, sender=Product)
def publish_product_event(sender, instance: Product, created: bool, **kwargs) -> None:
    publish_live_event(
        'product.created' if created else 'product.updated',
        {
            'id': instance.pk,
            'created': created,
            'tenant_id': instance.tenant_id,
            'category_id': instance.category_id,
            'is_active': instance.is_active,
            'is_deleted': instance.is_deleted,
        },
    )
