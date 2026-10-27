"""Opt-in incremental chain writer; never invoked by production scheduler yet.

Full archives remain handled by the existing guarded backup_tenant service.
Incremental writing requires a verified base and validates the resulting chain
before atomically publishing an archive. No automatic pruning is performed.
"""
import hashlib
import json
import os
import tempfile
import uuid
from contextlib import nullcontext
from pathlib import Path

from django.utils import timezone
from config.media_storage import media_read_lock
from .archive import verify
from .delta import fixture_digest
from .chain_recovery import recover_chain
from .incremental_archive import create_delta_archive
from .snapshot import SnapshotError, collect, open_media, fingerprint
from .staging import private_staging
from . import service


def media_manifest(files):
    result = {}
    for name in files:
        digest = hashlib.sha256()
        with open_media(name) as stream:
            before = fingerprint(os.fstat(stream.fileno()))
            if before != files.fingerprints[name]:
                raise SnapshotError('source_changed')
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
            if before != fingerprint(os.fstat(stream.fileno())):
                raise SnapshotError('source_changed')
        result[name] = digest.hexdigest()
        if result[name] != files.digests[name]:
            raise SnapshotError('source_changed')
    return result


def create_verified_increment(tenant_id, full_name, previous_increment_names=(), *, _lock_held=False, run=None):
    """Publish an encrypted incremental archive only after end-to-end recovery.

    Names must be obtained from trusted, successful BackupRun records, not HTTP.
    Caller is responsible for durable run history and daily scheduling.
    """
    tenant_id = int(tenant_id)
    if not service.eligible(tenant_id):
        raise SnapshotError('subscription_inactive')
    with service.pinned_root() as root, media_read_lock():
        directory = root / f'tenant-{tenant_id}'
        with service.pinned_tenant(directory) as directory, (nullcontext() if _lock_held else service.tenant_lock(directory)):
            service.write_guard()
            names = [full_name, *previous_increment_names]
            if not names or any(not isinstance(name, str) or Path(name).name != name or not name.endswith('.cvb') for name in names):
                raise SnapshotError('invalid_chain')
            paths = [directory / name for name in names]
            if any(path.is_symlink() or not path.is_file() for path in paths):
                raise SnapshotError('invalid_chain')
            verify(paths[0], tenant_id)
            with private_staging(tenant_id) as temporary:
                os.chmod(temporary, 0o700)
                state = Path(temporary) / 'state'
                previous_fixture = recover_chain(paths[0], paths[1:], tenant_id, state)
                previous_media = {}
                media_root = state / 'media'
                if media_root.exists():
                    for file in media_root.rglob('*'):
                        if file.is_file():
                            digest = hashlib.sha256()
                            with file.open('rb') as stream:
                                while chunk := stream.read(1024 * 1024):
                                    digest.update(chunk)
                            previous_media[file.relative_to(media_root).as_posix()] = digest.hexdigest()
                with service.consistent_read():
                    fixture_bytes, files = collect(tenant_id)
                current_fixture = json.loads(fixture_bytes)
                current_media = media_manifest(files)
                name = f'{timezone.now():%Y%m%dT%H%M%S}-{uuid.uuid4().hex}.delta.cvb'
                partial = directory / (name + '.partial')
                try:
                    create_delta_archive(partial, tenant_id, previous_fixture, current_fixture,
                                         previous_media, current_media, open_media, service.write_guard)
                    candidate = Path(temporary) / 'candidate'
                    recovered = recover_chain(paths[0], [*paths[1:], partial], tenant_id, candidate)
                    if fixture_digest(recovered) != fixture_digest(current_fixture):
                        raise SnapshotError('checksum_mismatch')
                    if not service.eligible(tenant_id):
                        raise SnapshotError('subscription_inactive')
                    service.write_guard()
                    if run is not None:
                        run.archive_name = name
                        run.save(update_fields=['archive_name'])
                    final = directory / name
                    os.replace(partial, final)
                    service.sync_directory(directory)
                    return name
                finally:
                    if partial.exists():
                        partial.unlink()
