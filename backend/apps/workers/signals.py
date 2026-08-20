from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.live import publish_live_event
from apps.workers.models import WorkerAttendance, WorkerProfile


@receiver(post_save, sender=WorkerProfile)
def publish_worker_event(sender, instance: WorkerProfile, created: bool, **kwargs) -> None:
    publish_live_event(
        'worker.created' if created else 'worker.updated',
        {
            'id': instance.pk,
            'created': created,
            'tenant_id': instance.tenant_id,
            'user_id': instance.user_id,
            'is_available': instance.is_available,
            'load_status': instance.load_status,
        },
    )


@receiver(post_save, sender=WorkerAttendance)
def publish_worker_attendance_event(sender, instance: WorkerAttendance, created: bool, **kwargs) -> None:
    publish_live_event(
        'worker.attendance.created' if created else 'worker.attendance.updated',
        {
            'id': instance.pk,
            'created': created,
            'tenant_id': instance.tenant_id,
            'worker_id': instance.worker_id,
            'event_type': instance.event_type,
        },
    )
