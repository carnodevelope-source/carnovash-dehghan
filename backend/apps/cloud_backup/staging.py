"""Private RAM-backed recovery staging; never plaintext on backup disks.

Call cleanup only while holding the corresponding tenant process lock.
A power loss/reboot discards tmpfs; a killed worker is cleaned on next attempt.
"""
import os
import shutil
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path
from .snapshot import SnapshotError


def staging_root():
    root = Path('/dev/shm')
    records = Path('/proc/self/mountinfo').read_text().splitlines()
    if root.is_symlink() or not any(
        len(parts) > 6 and parts[4] == str(root) and '-' in parts
        and parts[parts.index('-') + 1] == 'tmpfs'
        for parts in (line.split() for line in records)
    ):
        raise SnapshotError('unsafe_staging_filesystem')
    return root


def cleanup_staging(tenant_id):
    for item in staging_root().glob(f'carvash-verify-{os.geteuid()}-{int(tenant_id)}-*'):
        info = item.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise SnapshotError('unsafe_staging_directory')
        shutil.rmtree(item)


@contextmanager
def private_staging(tenant_id):
    with tempfile.TemporaryDirectory(
        prefix=f'carvash-verify-{os.geteuid()}-{int(tenant_id)}-', dir=staging_root()
    ) as temporary:
        os.chmod(temporary, 0o700)
        yield Path(temporary)
