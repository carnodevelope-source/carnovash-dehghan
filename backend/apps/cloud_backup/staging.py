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


def swap_disabled():
    # In a private cgroup namespace, swap.max=0 also prevents tmpfs pages from
    # reaching host swap. Host swap policy is never changed by this worker.
    try:
        if Path('/sys/fs/cgroup/memory.swap.max').read_text().strip() == '0':
            return True
    except OSError:
        pass
    try:
        return len(Path('/proc/swaps').read_text().splitlines()) <= 1
    except OSError:
        return False


def staging_root():
    root = Path('/dev/shm')
    records = Path('/proc/self/mountinfo').read_text().splitlines()
    if root.is_symlink() or not any(
        len(parts) > 6 and parts[4] == str(root) and '-' in parts
        and parts[parts.index('-') + 1] == 'tmpfs'
        for parts in (line.split() for line in records)
    ):
        raise SnapshotError('unsafe_staging_filesystem')
    if not swap_disabled():
        raise SnapshotError('unsafe_staging_swap')
    return root


@contextmanager
def _root_mutex(root):
    import fcntl
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def cleanup_staging(tenant_id=None):
    """Reap dead workers even for inactive tenants, never touch live staging."""
    import fcntl
    root = staging_root()
    tenant = '*' if tenant_id is None else str(int(tenant_id))
    removed = 0
    with _root_mutex(root):
        for item in root.glob(f'carvash-verify-{os.geteuid()}-{tenant}-*'):
            fd = os.open(item, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                info = os.fstat(fd)
                if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
                    raise SnapshotError('unsafe_staging_directory')
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    continue
                shutil.rmtree(item)
                removed += 1
            finally:
                os.close(fd)
    return removed


@contextmanager
def private_staging(tenant_id):
    import fcntl
    root = staging_root()
    temporary = None
    fd = None
    try:
        with _root_mutex(root):
            temporary = Path(tempfile.mkdtemp(
                prefix=f'carvash-verify-{os.geteuid()}-{int(tenant_id)}-', dir=root))
            os.chmod(temporary, 0o700)
            fd = os.open(temporary, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            fcntl.flock(fd, fcntl.LOCK_EX)
        yield temporary
    finally:
        # Keep the lease while deleting; a reaper can never remove live data.
        try:
            if temporary is not None:
                shutil.rmtree(temporary)
        finally:
            if fd is not None:
                os.close(fd)
