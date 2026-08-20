from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.auth.models import CarWashFeaturePurchase, SupportTicket, SupportTicketMessage
from apps.live import publish_live_event


@receiver(post_save, sender=SupportTicket)
def publish_support_ticket_event(sender, instance: SupportTicket, created: bool, **kwargs) -> None:
    publish_live_event(
        'support.ticket.created' if created else 'support.ticket.updated',
        {
            'id': instance.pk,
            'created': created,
            'tenant_id': instance.tenant_id,
            'status': instance.status,
            'priority': instance.priority,
        },
    )


@receiver(post_save, sender=SupportTicketMessage)
def publish_support_message_event(sender, instance: SupportTicketMessage, created: bool, **kwargs) -> None:
    publish_live_event(
        'support.message.created' if created else 'support.message.updated',
        {
            'id': instance.pk,
            'created': created,
            'ticket_id': instance.ticket_id,
            'tenant_id': instance.ticket.tenant_id,
        },
    )


@receiver(post_save, sender=CarWashFeaturePurchase)
def publish_feature_purchase_event(sender, instance: CarWashFeaturePurchase, created: bool, **kwargs) -> None:
    publish_live_event(
        'subscription.updated',
        {
            'id': instance.pk,
            'created': created,
            'tenant_id': instance.tenant_id,
            'feature_key': instance.feature_key,
            'is_active': instance.is_active,
        },
    )
