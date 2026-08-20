from __future__ import annotations

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.live import publish_live_event
from apps.vehicles.models import BlockedPlate, VehicleEntry, VehicleStatusLog


@receiver(post_save, sender=VehicleEntry)
def publish_vehicle_entry_event(sender, instance: VehicleEntry, created: bool, **kwargs) -> None:
    publish_live_event(
        'vehicle.created' if created else 'vehicle.updated',
        {
            'id': instance.pk,
            'created': created,
            'tenant_id': instance.tenant_id,
            'status': instance.status,
            'payment_status': instance.payment_status,
        },
    )


@receiver(post_save, sender=VehicleStatusLog)
def publish_vehicle_status_event(sender, instance: VehicleStatusLog, created: bool, **kwargs) -> None:
    publish_live_event(
        'vehicle.status.created' if created else 'vehicle.status.updated',
        {
            'id': instance.pk,
            'created': created,
            'tenant_id': instance.tenant_id,
            'vehicle_id': instance.vehicle_id,
            'from_status': instance.from_status,
            'to_status': instance.to_status,
        },
    )


@receiver(post_delete, sender=BlockedPlate)
def publish_blocked_plate_deleted_event(sender, instance: BlockedPlate, **kwargs) -> None:
    publish_live_event(
        'vehicle.blocked_plate.deleted',
        {
            'id': instance.pk,
            'tenant_id': instance.tenant_id,
            'plate_number': instance.plate_number,
        },
    )
