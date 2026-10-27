"""Opt-in Tehran daily execution. No production service enables this module."""
from datetime import datetime
from config.media_storage import media_read_lock
from django.utils import timezone
from .chain_history import latest_chain, successful_runs, verify_chain_files
from .chain_service import create_verified_increment
from .models import BackupRun
from .planner import plan_backup
from .schedule import TEHRAN, local_day
from . import service
from .snapshot import SnapshotError
from .staging import cleanup_staging


def run_moment(run):
    if run.scheduled_for is not None:
        return datetime.combine(run.scheduled_for, datetime.min.time(), tzinfo=TEHRAN)
    return run.started_at


def plan_tenant(tenant_id, now=None, *, directory=None):
    now = now or timezone.now()
    if directory is None:
        with service.locked_tenant(tenant_id) as pinned:
            return plan_tenant(tenant_id, now, directory=pinned)
    runs = successful_runs(tenant_id)
    try:
        base, deltas = latest_chain(tenant_id)
        healthy = base is not None
        if healthy:
            if directory is None:
                raise SnapshotError('chain_verification_required')
            verify_chain_files(directory, base, deltas, tenant_id)
    except (SnapshotError, OSError, ValueError):
        base, deltas, healthy = None, [], False
    latest = runs[-1] if runs else None
    return plan_backup(now, eligible=service.eligible(tenant_id),
        last_success=run_moment(latest) if latest else None,
        last_full=run_moment(base) if base else None,
        chain_healthy=healthy), base, deltas


def failure_code(exc):
    # Fixed vocabulary only: never exception messages, SQL, paths or keys.
    safe = {'subscription_inactive', 'source_changed', 'insufficient_space',
            'mount_unavailable', 'checksum_mismatch', 'missing_archive',
            'invalid_chain_history', 'unsafe_media', 'snapshot_limit_exceeded'}
    return str(exc) if isinstance(exc, SnapshotError) and str(exc) in safe else 'backup_failed'


def execute_tenant(tenant_id, now=None):
    tenant_id = int(tenant_id)
    now = now or timezone.now()
    day = local_day(now)
    run = None
    try:
        if not service.eligible(tenant_id):
            return None
        with service.locked_tenant(tenant_id) as directory, media_read_lock():
            # The lock owner is the only worker allowed to reconcile a dead run.
            BackupRun.objects.filter(tenant_id=tenant_id, status='running').update(
                status='failed', error_code='worker_interrupted', finished_at=timezone.now())
            cleanup_staging(tenant_id)
            for partial in directory.glob('*.partial'):
                service.write_guard()
                partial.unlink()
            plan, base, deltas = plan_tenant(tenant_id, now, directory=directory)
            if plan.action == 'skip':
                return None
            if plan.action == 'full':
                return service._backup_tenant_locked(tenant_id, preserve_chains=True, scheduled_for=day)
            run = BackupRun.objects.create(tenant_id=tenant_id, scheduled_for=day,
                backup_kind='incremental', base_run_id=base.pk,
                parent_run_id=deltas[-1].pk if deltas else base.pk)
            try:
                name = create_verified_increment(tenant_id, base.archive_name,
                    [item.archive_name for item in deltas], _lock_held=True, run=run)
                path = directory / name
                run.size_bytes = path.stat().st_size
                run.sha256 = service.archive_digest(path)
                run.verified_at = timezone.now()
                run.finished_at = timezone.now()
                run.recovery_status = 'integrity_verified'
                run.status = 'success'
                run.save()  # Must complete before the process lock is released.
                return run
            except Exception as exc:
                run.status = 'failed'
                run.recovery_status = 'unverified'
                run.error_code = failure_code(exc)
                run.finished_at = timezone.now()
                run.save()
                return run
    except Exception as exc:
        if isinstance(exc, SnapshotError) and str(exc) == 'already_running':
            return None
        if run is not None:
            raise  # Failed history persistence must reach the supervisor.
        return BackupRun.objects.create(tenant_id=tenant_id, scheduled_for=day,
            status='failed', error_code=failure_code(exc), finished_at=timezone.now())
