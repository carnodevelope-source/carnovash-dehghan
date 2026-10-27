"""Authenticated encrypted incremental archive format (isolated development).

A delta contains only fixture upserts/tombstones and changed media bytes.
It never writes plaintext backups to persistent storage.
"""
import hashlib
import io
import json
import os
import stat
import tarfile
from pathlib import Path

from django.conf import settings
from .archive import CHUNK, EncryptWriter, DecryptReader
from .delta import diff_fixture, apply_fixture, canonical
from .media_delta import diff_media, apply_media
from .snapshot import SnapshotError, add_bytes, safe_relative


def create_delta_archive(path, tenant_id, previous_fixture, current_fixture, previous_media, current_media, open_file, guard=lambda: None):
    """Write encrypted delta to a new private file; caller owns atomic publish.

    open_file(name) returns a binary context manager for the source media.
    Previous/current media maps must contain SHA256 of *all* referenced files.
    """
    changes = diff_fixture(previous_fixture, current_fixture)
    media_changes = diff_media(previous_media, current_media)
    metadata = {'version': 1, 'tenant_id': int(tenant_id), 'fixture': changes,
                'media': media_changes, 'result_media': dict(current_media)}
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    try:
        with os.fdopen(fd, 'wb') as output:
            writer = EncryptWriter(output, guard)
            with tarfile.open(fileobj=writer, mode='w|gz') as tar:
                add_bytes(tar, 'delta.json', canonical(metadata))
                for name, expected in media_changes['upserts'].items():
                    with open_file(name) as source:
                        info = os.fstat(source.fileno())
                        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                            raise SnapshotError('unsafe_media')
                        entry = tarfile.TarInfo('media/' + safe_relative(name))
                        entry.size, entry.mode = info.st_size, 0o600
                        class CheckedReader:
                            def __init__(self, stream):
                                self.stream, self.hash = stream, hashlib.sha256()
                            def read(self, size):
                                block = self.stream.read(size)
                                self.hash.update(block)
                                return block
                        reader = CheckedReader(source)
                        tar.addfile(entry, reader)
                        if reader.hash.hexdigest() != expected or os.fstat(source.fileno()).st_size != info.st_size:
                            raise SnapshotError('source_changed')
            writer.finish()
            output.flush()
            os.fsync(output.fileno())
    except BaseException:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass
        raise
    return metadata


def read_delta_archive(path, tenant_id, output_media):
    """Verify entire archive before returning; writes only to new staging dir.

    The staging directory must exist, be empty and be owner-only (0700).
    """
    destination = Path(output_media)
    if destination.is_symlink() or not destination.is_dir() or any(destination.iterdir()) or (destination.stat().st_mode & 0o077) or destination.stat().st_uid != os.geteuid():
        raise SnapshotError('unsafe_recovery_directory')
    observed = {}
    metadata = None
    with open(path, 'rb') as source:
        with io.BufferedReader(DecryptReader(source)) as stream:
            with tarfile.open(fileobj=stream, mode='r|gz') as tar:
                for member in tar:
                    name = safe_relative(member.name)
                    if not member.isfile() or name in observed or len(observed) > settings.CLOUD_BACKUP_MAX_FILES:
                        raise SnapshotError('invalid_member')
                    if name != 'delta.json' and not name.startswith('media/'):
                        raise SnapshotError('invalid_member')
                    if name == 'delta.json' and member.size > settings.CLOUD_BACKUP_MAX_JSON_BYTES:
                        raise SnapshotError('snapshot_limit_exceeded')
                    digest = hashlib.sha256()
                    if name == 'delta.json':
                        payload = tar.extractfile(member).read()
                        digest.update(payload)
                        metadata = json.loads(payload)
                    else:
                        target = destination / name
                        if any(parent.is_symlink() for parent in [target, *target.parents] if parent.is_relative_to(destination)) or not target.resolve().is_relative_to(destination.resolve()):
                            raise SnapshotError('unsafe_media')
                        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                        with open(target, 'xb') as output:
                            os.chmod(target, 0o600)
                            reader = tar.extractfile(member)
                            while chunk := reader.read(CHUNK):
                                digest.update(chunk)
                                output.write(chunk)
                    observed[name] = digest.hexdigest()
            while stream.read(CHUNK):
                pass
    if not isinstance(metadata, dict) or metadata.get('version') != 1 or metadata.get('tenant_id') != int(tenant_id):
        raise SnapshotError('wrong_tenant')
    changes = metadata.get('media')
    if not isinstance(changes, dict) or not isinstance(changes.get('upserts'), dict) or not isinstance(changes.get('deletes'), list) or set(observed) != {'delta.json'} | {'media/' + name for name in changes['upserts']}:
        raise SnapshotError('invalid_manifest')
    from .media_delta import validate_media_manifest
    validate_media_manifest(changes['upserts'])
    validate_media_manifest(metadata.get('result_media'))
    for name, expected in changes['upserts'].items():
        if observed['media/' + name] != expected:
            raise SnapshotError('checksum_mismatch')
    return metadata


def reconstruct_delta(previous_fixture, previous_media, metadata):
    """Verify fixture checksum and media transition, then return new state."""
    fixture = apply_fixture(previous_fixture, metadata['fixture'])
    media = apply_media(previous_media, metadata['media'])
    if media != metadata['result_media']:
        raise SnapshotError('checksum_mismatch')
    return fixture, media
