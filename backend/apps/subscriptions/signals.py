from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.live import publish_live_event
from apps.subscriptions.models import ServiceOrder, ServicePaymentRecord, ServiceSubscription


@receiver(post_save, sender=ServiceSubscription)
def publish_subscription_event(sender, instance: ServiceSubscription, created: bool, **kwargs) -> None:
    publish_live_event(
        'subscription.created' if created else 'subscription.updated',
        {
            'id': instance.pk,
            'created': created,
            'tenant_id': instance.tenant_id,
            'status': instance.status,
            'payment_status': instance.payment_status,
            'product_id': instance.product_id,
        },
    )


@receiver(post_save, sender=ServiceOrder)
def publish_subscription_order_event(sender, instance: ServiceOrder, created: bool, **kwargs) -> None:
    publish_live_event(
        'subscription.order.created' if created else 'subscription.order.updated',
        {
            'id': instance.pk,
            'created': created,
            'tenant_id': instance.tenant_id,
            'status': instance.status,
            'product_id': instance.product_id,
            'subscription_id': instance.subscription_id,
        },
    )


@receiver(post_save, sender=ServicePaymentRecord)
def publish_subscription_payment_event(sender, instance: ServicePaymentRecord, created: bool, **kwargs) -> None:
    publish_live_event(
        'subscription.payment.created' if created else 'subscription.payment.updated',
        {
            'id': instance.pk,
            'created': created,
            'tenant_id': instance.tenant_id,
            'subscription_id': instance.subscription_id,
            'order_id': instance.order_id,
            'kind': instance.kind,
        },
    )
