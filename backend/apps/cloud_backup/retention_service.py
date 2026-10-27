"""Verified tenant-scoped retention, explicit reviewed-plan execution only.

Deletes oldest chains tip-first. Before unlink, history is durably marked
'deleting'. Interrupted deletion can only finish after replacement chains verify.
Unknown archives, corrupt archives or metadata ambiguities fail closed.
"""
import hashlib
import json
from datetime import timedelta
from pathlib import Path
from django.db.models import Q
from django.utils import timezone
from .models import BackupRun
from .chain_history import verify_chain_files
from .scheduled_chain import run_moment
from .schedule import local_day, RETENTION_DAYS
from .snapshot import SnapshotError
from . import service


def chains_for(runs):
    chains, membership = [], {}
    for run in runs:
        if run.backup_kind == 'full':
            chains.append([run])
            membership[run.pk] = len(chains) - 1
        elif (run.backup_kind == 'incremental' and run.parent_run_id in membership):
            index = membership[run.parent_run_id]
            chain = chains[index]
            if chain[-1].pk != run.parent_run_id or chain[0].pk != run.base_run_id:
                raise SnapshotError('invalid_chain_history')
            if (run_moment(run), run.pk) <= (run_moment(chain[-1]), chain[-1].pk):
                raise SnapshotError('invalid_chain_history')
            chain.append(run)
            membership[run.pk] = index
        else:
            raise SnapshotError('invalid_chain_history')
    return chains


def _inspect(tenant_id, directory, now):
    runs = list(BackupRun.objects.filter(tenant_id=tenant_id,
        status__in=['success', 'deleting']).order_by('started_at', 'pk'))
    active, interrupted = [], []
    for run in runs:
        if not run.archive_name or Path(run.archive_name).name != run.archive_name:
            raise SnapshotError('invalid_chain_history')
        if run.status == 'deleting' and not (directory / run.archive_name).exists():
            interrupted.append(run)
        else:
            if run.recovery_status != 'integrity_verified':
                raise SnapshotError('unverified_archive')
            active.append(run)
    observed = {p.name for p in directory.glob('*.cvb')}
    if observed != {run.archive_name for run in active}:
        raise SnapshotError('unmanaged_archive')
    chains = chains_for(active)
    if not chains:
        raise SnapshotError('no_verified_replacement')
    cutoff = local_day(now) - timedelta(days=RETENTION_DAYS)
    keep = {i for i, chain in enumerate(chains) if local_day(run_moment(chain[-1])) >= cutoff}
    keep.update(range(max(0, len(chains) - 3), len(chains)))
    if not any(local_day(run_moment(chain[-1])) >= cutoff for i, chain in enumerate(chains) if i in keep):
        raise SnapshotError('no_verified_replacement')
    # Verify every link, including old candidates. Suspicion never authorizes deletion.
    for chain in chains:
        if any(local_day(run_moment(item)) > local_day(now) for item in chain):
            raise SnapshotError('future_archive')
        verify_chain_files(directory, chain[0], chain[1:], tenant_id)
    candidates = [run for i, chain in enumerate(chains) if i not in keep for run in reversed(chain)]
    retained = [run for i, chain in enumerate(chains) if i in keep for run in chain]
    deleting_ids = {run.pk for run in interrupted}
    if any(run.parent_run_id in deleting_ids or run.base_run_id in deleting_ids for run in active):
        raise SnapshotError('invalid_chain_history')
    payload = {'tenant': int(tenant_id), 'day': str(local_day(now)),
               'retained': [(r.pk, r.archive_name, r.sha256) for r in retained],
               'delete': [(r.pk, r.archive_name, r.sha256) for r in candidates],
               'interrupted': [(r.pk, r.archive_name) for r in interrupted]}
    token = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return payload, token, candidates, interrupted


def retain_tenant(tenant_id, *, now=None, execute=False, reviewed_token=None):
    now = now or timezone.now()
    tenant_id = int(tenant_id)
    with service.locked_tenant(tenant_id) as directory:
        if not service.eligible(tenant_id):
            raise SnapshotError('subscription_inactive')
        payload, token, candidates, interrupted = _inspect(tenant_id, directory, now)
        if not execute:
            return dict(payload, token=token, dry_run=True)
        if reviewed_token != token:
            raise SnapshotError('retention_plan_changed')
        # Reconciliation changes history only after all surviving chains verified.
        for run in interrupted:
            run.status = 'pruned'
            run.save(update_fields=['status'])
        for run in candidates:
            if not service.eligible(tenant_id):
                raise SnapshotError('subscription_inactive')
            if BackupRun.objects.filter(tenant_id=tenant_id, status='success').filter(
                    Q(parent_run_id=run.pk) | Q(base_run_id=run.pk)).exists():
                raise SnapshotError('archive_still_required')
            service.write_guard()
            path = directory / run.archive_name
            if path.is_symlink() or service.archive_digest(path) != run.sha256:
                raise SnapshotError('checksum_mismatch')
            run.status = 'deleting'
            run.save(update_fields=['status'])
            path.unlink()
            service.sync_directory(directory)
            run.status = 'pruned'
            run.save(update_fields=['status'])
        return dict(payload, token=token, dry_run=False)
