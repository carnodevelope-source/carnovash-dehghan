from __future__ import annotations

from django.db import transaction
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
            'actor_user_id': instance.created_by_id,
            'status': instance.status,
            'priority': instance.priority,
        },
    )
    if not created or not instance.pk:
        return

    ticket_id = instance.pk

    def _notify_hq_sms():
        try:
            from apps.auth.support_tickets import notify_hq_alert_ticket_sms

            notify_hq_alert_ticket_sms(ticket_id)
        except Exception as exc:
            print(f'hq ticket sms webhook failed for ticket {ticket_id}: {exc}')

    # After commit so payment/registration transactions don't SMS half-created rows,
    # and so duplicate callers + this webhook share one idempotent send.
    transaction.on_commit(_notify_hq_sms)


@receiver(post_save, sender=SupportTicketMessage)
def publish_support_message_event(sender, instance: SupportTicketMessage, created: bool, **kwargs) -> None:
    publish_live_event(
        'support.message.created' if created else 'support.message.updated',
        {
            'id': instance.pk,
            'created': created,
            'ticket_id': instance.ticket_id,
            'tenant_id': instance.ticket.tenant_id,
            'actor_user_id': instance.sender_id,
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
