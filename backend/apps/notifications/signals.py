from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.live import publish_live_event
from apps.notifications.models import CustomerGroup, ImportedCustomer, NotificationLog, SmsTemplate


@receiver(post_save, sender=NotificationLog)
def publish_notification_log_event(sender, instance: NotificationLog, created: bool, **kwargs) -> None:
    publish_live_event(
        'notification.created' if created else 'notification.updated',
        {
            'id': instance.pk,
            'created': created,
            'tenant_id': instance.tenant_id,
            'channel': instance.channel,
            'status': instance.status,
        },
    )


@receiver(post_save, sender=SmsTemplate)
def publish_sms_template_event(sender, instance: SmsTemplate, created: bool, **kwargs) -> None:
    publish_live_event(
        'notification.template.created' if created else 'notification.template.updated',
        {
            'id': instance.pk,
            'created': created,
            'tenant_id': instance.tenant_id,
            'is_active': instance.is_active,
        },
    )


@receiver(post_save, sender=CustomerGroup)
def publish_customer_group_event(sender, instance: CustomerGroup, created: bool, **kwargs) -> None:
    publish_live_event(
        'notification.customer_group.created' if created else 'notification.customer_group.updated',
        {
            'id': instance.pk,
            'created': created,
            'tenant_id': instance.tenant_id,
            'is_active': instance.is_active,
        },
    )


@receiver(post_save, sender=ImportedCustomer)
def publish_imported_customer_event(sender, instance: ImportedCustomer, created: bool, **kwargs) -> None:
    publish_live_event(
        'notification.customer.created' if created else 'notification.customer.updated',
        {
            'id': instance.pk,
            'created': created,
            'tenant_id': instance.tenant_id,
        },
    )
