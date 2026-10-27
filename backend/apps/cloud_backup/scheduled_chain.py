"""Opt-in daily Tehran chain scheduler. Production command remains unchanged.

This callable is deliberately separate until a disposable MySQL recovery
rehearsal validates it. Never enable on production before that rehearsal.
"""
from django.utils import timezone
from .chain_history import latest_chain, successful_runs
from .chain_service import create_verified_increment
from .models import BackupRun
from .planner import plan_backup
from .service import backup_tenant, eligible, pinned_root, archive_digest
from .snapshot import SnapshotError


def plan_tenant(tenant_id, now=None):
    now = now or timezone.now()
    runs = successful_runs(tenant_id)
    try:
        base, deltas = latest_chain(tenant_id)
        healthy = True
    except SnapshotError:
        base, deltas, healthy = None, [], False
    latest = runs[-1] if runs else None
    return plan_backup(now, eligible=eligible(tenant_id),
        last_success=(latest.finished_at or latest.started_at) if latest else None,
        last_full=(base.finished_at or base.started_at) if base else None,
        chain_healthy=healthy), base, deltas


def execute_tenant(tenant_id, now=None):
    """One opt-in cycle; call from a dedicated process only, never web workers."""
    tenant_id = int(tenant_id)
    plan, base, deltas = plan_tenant(tenant_id, now)
    if plan.action == 'skip':
        return None
    if plan.action == 'full':
        return backup_tenant(tenant_id, scheduled=False)
    if base is None:
        raise SnapshotError('missing_full_base')
    # chain_service performs guarded encryption, full restore verification and
    # atomic publish. A failed publication must not create a success record.
    name = create_verified_increment(tenant_id, base.archive_name, [run.archive_name for run in deltas])
    with pinned_root() as root:
        path = root / f'tenant-{tenant_id}' / name
        if path.is_symlink() or not path.is_file():
            raise SnapshotError('missing_archive')
        size, digest = path.stat().st_size, archive_digest(path)
    run = BackupRun.objects.create(tenant_id=tenant_id, status='success',
        backup_kind='incremental', base_run_id=base.pk,
        parent_run_id=deltas[-1].pk if deltas else base.pk,
        archive_name=name, size_bytes=size, sha256=digest,
        verified_at=timezone.now(), finished_at=timezone.now(),
        recovery_status='integrity_verified')
    return run
