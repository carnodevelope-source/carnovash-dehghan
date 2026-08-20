from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.live import publish_live_event
from apps.payments.models import CashflowTransaction, Payment, WalletGatewayRequest


@receiver(post_save, sender=Payment)
def publish_payment_event(sender, instance: Payment, created: bool, **kwargs) -> None:
    publish_live_event(
        'payment.created' if created else 'payment.updated',
        {
            'id': instance.pk,
            'created': created,
            'tenant_id': instance.tenant_id,
            'amount': str(instance.amount),
            'method': instance.method,
        },
    )


@receiver(post_save, sender=WalletGatewayRequest)
def publish_wallet_gateway_event(sender, instance: WalletGatewayRequest, created: bool, **kwargs) -> None:
    publish_live_event(
        'payment.gateway.created' if created else 'payment.gateway.updated',
        {
            'id': instance.pk,
            'created': created,
            'tenant_id': instance.tenant_id,
            'wallet_id': instance.wallet_id,
            'status': instance.status,
        },
    )


@receiver(post_save, sender=CashflowTransaction)
def publish_cashflow_event(sender, instance: CashflowTransaction, created: bool, **kwargs) -> None:
    publish_live_event(
        'payment.cashflow.created' if created else 'payment.cashflow.updated',
        {
            'id': instance.pk,
            'created': created,
            'tenant_id': instance.tenant_id,
            'wallet_id': instance.wallet_id,
            'direction': instance.direction,
        },
    )
