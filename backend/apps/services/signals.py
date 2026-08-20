from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.live import publish_live_event
from apps.services.models import GeneralSettings, Service, ServiceCategory


@receiver(post_save, sender=ServiceCategory)
def publish_service_category_event(sender, instance: ServiceCategory, created: bool, **kwargs) -> None:
    publish_live_event(
        'service.category.created' if created else 'service.category.updated',
        {
            'id': instance.pk,
            'created': created,
            'tenant_id': instance.tenant_id,
            'is_active': instance.is_active,
        },
    )


@receiver(post_save, sender=Service)
def publish_service_event(sender, instance: Service, created: bool, **kwargs) -> None:
    publish_live_event(
        'service.created' if created else 'service.updated',
        {
            'id': instance.pk,
            'created': created,
            'tenant_id': instance.tenant_id,
            'category_id': instance.category_id,
            'is_active': instance.is_active,
            'is_deleted': instance.is_deleted,
        },
    )


@receiver(post_save, sender=GeneralSettings)
def publish_settings_event(sender, instance: GeneralSettings, created: bool, **kwargs) -> None:
    publish_live_event(
        'settings.updated',
        {
            'id': instance.pk,
            'created': created,
            'tenant_id': instance.tenant_id,
        },
    )
