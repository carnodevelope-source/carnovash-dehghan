"""Recover a verified full archive plus ordered incremental archives.

Recovery is always to a NEW private directory, never a live media volume.
An optional isolated recovery DB can be loaded separately after validation.
"""
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

from .archive import verify, validate_fixture
from .delta import canonical
from .incremental_archive import read_delta_archive, reconstruct_delta
from .snapshot import SnapshotError, safe_relative


def digest_file(path):
    value = hashlib.sha256()
    with open(path, 'rb') as stream:
        while block := stream.read(1024 * 1024):
            value.update(block)
    return value.hexdigest()


def recover_chain(full_archive, incremental_archives, tenant_id, output):
    """Verify base and each delta, reconstruct a tenant-scoped staging tree.

    output must not exist; on any failure it is removed, never published.
    """
    output = Path(output)
    if output.exists() or output.is_symlink() or output.parent.is_symlink():
        raise SnapshotError('unsafe_recovery_directory')
    output.mkdir(mode=0o700)
    try:
        verify(full_archive, tenant_id, output=output)
        fixture_path = output / 'fixture.json'
        fixture = json.loads(fixture_path.read_bytes())
        media_root = output / 'media'
        media = {}
        if media_root.exists():
            for file in media_root.rglob('*'):
                if file.is_file():
                    name = file.relative_to(media_root).as_posix()
                    media[safe_relative(name)] = digest_file(file)
        for archive in incremental_archives:
            with tempfile.TemporaryDirectory(prefix='increment-', dir=output) as temp:
                stage = Path(temp)
                os.chmod(stage, 0o700)
                metadata = read_delta_archive(archive, tenant_id, stage)
                next_fixture, next_media = reconstruct_delta(fixture, media, metadata)
                validate_fixture(next_fixture, tenant_id)
                changes = metadata['media']
                # Preflight all media mutations before changing the recovered tree.
                for name in changes['deletes']:
                    target = media_root / safe_relative(name)
                    if target.is_symlink() or not target.is_file() or digest_file(target) != media[name]:
                        raise SnapshotError('unsafe_media')
                for name in changes['upserts']:
                    target = media_root / safe_relative(name)
                    if target.is_symlink() or (target.exists() and not target.is_file()):
                        raise SnapshotError('unsafe_media')
                for name in changes['deletes']:
                    target = media_root / safe_relative(name)
                    if target.is_symlink() or not target.is_file():
                        raise SnapshotError('unsafe_media')
                    target.unlink()
                for name in changes['upserts']:
                    source = stage / 'media' / safe_relative(name)
                    target = media_root / safe_relative(name)
                    if target.is_symlink() or source.is_symlink():
                        raise SnapshotError('unsafe_media')
                    target.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
                    os.replace(source, target)
                fixture = next_fixture
                media = next_media
                fixture_path.write_bytes(canonical(fixture))
                os.chmod(fixture_path, 0o600)
        validate_fixture(fixture, tenant_id)
        for name, expected in media.items():
            if digest_file(media_root / safe_relative(name)) != expected:
                raise SnapshotError('checksum_mismatch')
        observed = {file.relative_to(media_root).as_posix() for file in media_root.rglob('*') if file.is_file()} if media_root.exists() else set()
        if observed != set(media):
            raise SnapshotError('unexpected_media')
        return fixture
    except BaseException:
        shutil.rmtree(output)
        raise
