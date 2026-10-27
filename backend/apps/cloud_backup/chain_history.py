"""Trusted backup run history and verified chain selection."""
from .models import BackupRun
from .snapshot import SnapshotError


def successful_runs(tenant_id):
    return list(BackupRun.objects.filter(tenant_id=tenant_id, status='success',
                recovery_status='integrity_verified').exclude(archive_name='').order_by('started_at', 'pk'))


def latest_chain(tenant_id):
    """Return (base_run, ordered_deltas), or (None, []) if no usable chain.

    Do not fall back silently to an older chain if the latest one is corrupt.
    Caller should create a new full archive in that situation.
    """
    runs = successful_runs(tenant_id)
    if not runs:
        return None, []
    last = runs[-1]
    if last.backup_kind == 'full':
        return last, []
    if last.backup_kind != 'incremental':
        raise SnapshotError('invalid_chain_history')
    index = {run.pk: run for run in runs}
    deltas = []
    visited = set()
    current = last
    while current.backup_kind == 'incremental':
        if current.pk in visited or current.parent_run_id not in index:
            raise SnapshotError('invalid_chain_history')
        visited.add(current.pk)
        deltas.append(current)
        parent = index[current.parent_run_id]
        if parent.tenant_id != tenant_id or current.base_run_id is None:
            raise SnapshotError('invalid_chain_history')
        current = parent
    if current.backup_kind != 'full' or any(delta.base_run_id != current.pk for delta in deltas):
        raise SnapshotError('invalid_chain_history')
    deltas.reverse()
    return current, deltas
