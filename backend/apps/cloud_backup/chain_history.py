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
        if (parent.tenant_id != int(tenant_id) or current.base_run_id is None
                or (parent.started_at, parent.pk) >= (current.started_at, current.pk)):
            raise SnapshotError('invalid_chain_history')
        current = parent
    if current.backup_kind != 'full' or any(delta.base_run_id != current.pk for delta in deltas):
        raise SnapshotError('invalid_chain_history')
    deltas.reverse()
    return current, deltas


def verify_chain_files(directory, base, deltas, tenant_id):
    """Authenticate stored bytes and reconstruct every link before planning."""
    from pathlib import Path
    from .service import archive_digest
    from .chain_recovery import recover_chain
    from .staging import private_staging
    if base is None:
        return
    paths = []
    for run in [base, *deltas]:
        name = run.archive_name
        if not name or Path(name).name != name or not name.endswith('.cvb'):
            raise SnapshotError('invalid_chain_history')
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise SnapshotError('missing_archive')
        info = path.stat()
        import os, stat
        if (info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o600
                or info.st_nlink != 1 or info.st_size != run.size_bytes
                or archive_digest(path) != run.sha256):
            raise SnapshotError('checksum_mismatch')
        paths.append(path)
    with private_staging(tenant_id) as staging:
        recover_chain(paths[0], paths[1:], tenant_id, staging / 'recovered')
