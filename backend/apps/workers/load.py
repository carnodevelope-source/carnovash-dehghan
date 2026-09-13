"""Worker busy/free load and assignment hold helpers."""

from datetime import datetime, time

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from .models import WorkerProfile


# Keep as plain strings to avoid circular imports with vehicles.
OPEN_VEHICLE_STATUSES = {
    'entered',
    'assigned',
    'in_progress',
    'ready_to_settle',
}

_STALE_HOLD_SWEEP_TTL_SECONDS = 60


def worker_ids_from_job(job):
    if not job:
        return []
    ordered = []
    snapshot = job.assigned_workers_snapshot if isinstance(job.assigned_workers_snapshot, list) else []
    for item in snapshot:
        raw = item.get('id') if isinstance(item, dict) else item
        try:
            worker_id = int(raw)
        except (TypeError, ValueError):
            continue
        if worker_id > 0 and worker_id not in ordered:
            ordered.append(worker_id)
    assigned_id = getattr(job, 'assigned_worker_id', None)
    if assigned_id and int(assigned_id) not in ordered:
        ordered.insert(0, int(assigned_id))
    return ordered


def _load_status_for_count(count):
    if count <= 0:
        return WorkerProfile.LoadStatus.FREE
    if count == 1:
        return WorkerProfile.LoadStatus.NORMAL
    return WorkerProfile.LoadStatus.BUSY


def _local_day_start(now=None):
    local_now = timezone.localtime(now or timezone.now())
    return timezone.make_aware(datetime.combine(local_now.date(), time.min))


def _tenant_id(tenant):
    if tenant is None:
        return None
    return getattr(tenant, 'pk', None) or getattr(tenant, 'id', None) or tenant


def _publish_queue_updated(tenant):
    """One live event for a batch load change — never N worker.updated saves."""
    tenant_id = _tenant_id(tenant)
    if not tenant_id:
        return
    from apps.live import publish_live_event

    publish_live_event(
        'worker.queue.updated',
        {
            'tenant_id': tenant_id,
            'entity_id': tenant_id,
        },
    )


def apply_worker_load_delta(worker_ids, delta, *, mark_assigned=False, tenant=None, publish=True):
    """Increment/decrement active job counts and sync load_status."""
    normalized_ids = []
    for raw in worker_ids or []:
        try:
            worker_id = int(raw)
        except (TypeError, ValueError):
            continue
        if worker_id > 0 and worker_id not in normalized_ids:
            normalized_ids.append(worker_id)
    if not normalized_ids or not delta:
        return False

    now = timezone.now()
    queryset = WorkerProfile.objects.select_for_update().filter(
        id__in=normalized_ids,
        user__role='worker',
        is_deleted=False,
    )
    if tenant is not None:
        queryset = queryset.filter(tenant=tenant)

    changed = False
    for worker in queryset:
        next_count = max(0, int(worker.active_jobs_count or 0) + int(delta))
        update_fields = {
            'active_jobs_count': next_count,
            'load_status': _load_status_for_count(next_count),
            'updated_at': now,
        }
        if mark_assigned and delta > 0:
            update_fields['last_assigned_at'] = now
        WorkerProfile.objects.filter(pk=worker.pk).update(**update_fields)
        changed = True

    if changed and publish:
        _publish_queue_updated(tenant)
    return changed


def sync_held_job_workers(job, previous_ids, next_ids, *, tenant=None):
    """Adjust load when the assigned set changes while the job still holds workers."""
    if not job or not getattr(job, 'workers_held', False):
        return
    previous = {int(item) for item in (previous_ids or []) if item}
    nxt = {int(item) for item in (next_ids or []) if item}
    removed = previous - nxt
    added = nxt - previous
    resolved_tenant = tenant or getattr(job, 'tenant', None)
    changed = False
    if removed:
        changed = apply_worker_load_delta(removed, -1, tenant=resolved_tenant, publish=False) or changed
    if added:
        changed = apply_worker_load_delta(added, 1, mark_assigned=True, tenant=resolved_tenant, publish=False) or changed
    if changed:
        _publish_queue_updated(resolved_tenant)


@transaction.atomic
def hold_job_workers(job, *, tenant=None, force=False):
    """Mark job workers as busy for an open vehicle."""
    if not job:
        return False
    vehicle = getattr(job, 'vehicle', None)
    if vehicle and getattr(vehicle, 'status', None) not in OPEN_VEHICLE_STATUSES and not force:
        return False

    worker_ids = worker_ids_from_job(job)
    if not worker_ids:
        if getattr(job, 'workers_held', False):
            job.workers_held = False
            job.workers_freed_at = timezone.now()
            job.save(update_fields=['workers_held', 'workers_freed_at', 'updated_at'])
        return False

    if getattr(job, 'workers_held', False):
        # Already holding — never double-increment load.
        return False

    apply_worker_load_delta(worker_ids, 1, mark_assigned=True, tenant=tenant or job.tenant)
    job.workers_held = True
    job.workers_freed_at = None
    job.save(update_fields=['workers_held', 'workers_freed_at', 'updated_at'])
    return True


@transaction.atomic
def free_job_workers(job, *, tenant=None):
    """Release busy hold so workers return to the free queue (assignment stays on the job)."""
    if not job or not getattr(job, 'workers_held', False):
        return False

    worker_ids = worker_ids_from_job(job)
    if worker_ids:
        apply_worker_load_delta(worker_ids, -1, tenant=tenant or job.tenant)

    job.workers_held = False
    job.workers_freed_at = timezone.now()
    job.save(update_fields=['workers_held', 'workers_freed_at', 'updated_at'])
    return True


@transaction.atomic
def free_stale_worker_holds(tenant, *, force=False):
    """Free holds on open cars from previous local days so the turn queue matches today's board."""
    if not tenant:
        return 0
    from apps.vehicles.models import VehicleJob

    tenant_id = _tenant_id(tenant)
    cache_key = f'worker-stale-hold-sweep:{tenant_id}'
    if not force and cache.get(cache_key):
        return 0

    day_start = _local_day_start()
    stale_filter = {
        'tenant': tenant,
        'workers_held': True,
        'vehicle__status__in': OPEN_VEHICLE_STATUSES,
    }
    has_stale = (
        VehicleJob.objects
        .filter(**stale_filter)
        .exclude(vehicle__check_in_at__gte=day_start)
        .exists()
    )
    if not has_stale:
        cache.set(cache_key, 1, _STALE_HOLD_SWEEP_TTL_SECONDS)
        return 0

    stale_jobs = list(
        VehicleJob.objects
        .select_for_update()
        .select_related('vehicle')
        .filter(**stale_filter)
        .exclude(vehicle__check_in_at__gte=day_start)
    )
    freed = 0
    for job in stale_jobs:
        worker_ids = worker_ids_from_job(job)
        if worker_ids:
            apply_worker_load_delta(worker_ids, -1, tenant=tenant, publish=False)
        job.workers_held = False
        job.workers_freed_at = timezone.now()
        job.save(update_fields=['workers_held', 'workers_freed_at', 'updated_at'])
        freed += 1

    recompute_worker_loads_for_tenant(tenant, publish=False)
    _publish_queue_updated(tenant)
    cache.set(cache_key, 1, _STALE_HOLD_SWEEP_TTL_SECONDS)
    return freed


def recompute_worker_loads_for_tenant(tenant, *, publish=True):
    """Rebuild active_jobs_count/load_status from currently held open jobs for today only."""
    if not tenant:
        return
    from apps.vehicles.models import VehicleJob

    day_start = _local_day_start()
    held_jobs = (
        VehicleJob.objects
        .select_related('vehicle')
        .filter(
            tenant=tenant,
            workers_held=True,
            vehicle__status__in=OPEN_VEHICLE_STATUSES,
            vehicle__check_in_at__gte=day_start,
        )
    )
    counts = {}
    for job in held_jobs:
        for worker_id in worker_ids_from_job(job):
            counts[worker_id] = counts.get(worker_id, 0) + 1

    now = timezone.now()
    changed = False
    workers = WorkerProfile.objects.filter(tenant=tenant, user__role='worker', is_deleted=False)
    for worker in workers:
        next_count = int(counts.get(worker.id, 0))
        next_status = _load_status_for_count(next_count)
        if (
            int(worker.active_jobs_count or 0) == next_count
            and worker.load_status == next_status
        ):
            continue
        WorkerProfile.objects.filter(pk=worker.pk).update(
            active_jobs_count=next_count,
            load_status=next_status,
            updated_at=now,
        )
        changed = True

    if changed and publish:
        _publish_queue_updated(tenant)
