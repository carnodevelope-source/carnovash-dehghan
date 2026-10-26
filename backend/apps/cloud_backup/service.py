import errno
import hashlib
import json
import os
import shutil
import tarfile
import uuid
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone

from apps.auth.models import CarWashFeaturePurchase
from .archive import CHUNK, EncryptWriter, verify
from .models import BackupRun
from .snapshot import SnapshotError, add_bytes, collect, media_path


def eligible(tenant_id):
    return CarWashFeaturePurchase.objects.filter(
        tenant_id=tenant_id, feature_key='cloud_storage', is_active=True,
    ).exists()


def mount_guard():
    root = Path(settings.CLOUD_BACKUP_ROOT)
    expected = settings.CLOUD_BACKUP_DEVICE
    if not expected or not root.is_absolute() or str(root.resolve()) != str(root):
        raise SnapshotError('mount_unavailable')
    try:
        stat = root.stat()
        device = f'{os.major(stat.st_dev)}:{os.minor(stat.st_dev)}'
        records = Path(settings.CLOUD_BACKUP_HOST_MOUNTINFO).read_text().splitlines()
        host_mounted = any(
            len(parts := line.split()) > 6 and parts[2] == expected and parts[4] == str(root)
            for line in records
        )
        if not root.is_mount() or device != expected or not host_mounted:
            raise SnapshotError('mount_unavailable')
    except OSError:
        raise SnapshotError('mount_unavailable') from None


@contextmanager
def pinned_root():
    # Every write resolves via this open directory, so an unmount race can never
    # redirect writes to the SSD directory hidden underneath the mount.
    mount_guard()
    fd = os.open(settings.CLOUD_BACKUP_ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        mount_guard()
        if os.fstat(fd).st_dev != os.stat(settings.CLOUD_BACKUP_ROOT).st_dev:
            raise SnapshotError('mount_unavailable')
        yield Path(f'/proc/self/fd/{fd}')
    finally:
        os.close(fd)


def write_guard():
    mount_guard()
    if shutil.disk_usage(settings.CLOUD_BACKUP_ROOT).free < settings.CLOUD_BACKUP_MIN_FREE_BYTES:
        raise SnapshotError('insufficient_space')


@contextmanager
def consistent_read():
    if connection.in_atomic_block:
        raise SnapshotError('nested_snapshot_transaction')
    if connection.vendor == 'mysql':
        with connection.cursor() as cursor:
            cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
    elif connection.vendor != 'sqlite':
        raise SnapshotError('unsupported_database')
    with transaction.atomic():
        yield


class DigestReader:
    def __init__(self, source):
        self.source, self.digest = source, hashlib.sha256()

    def read(self, size):
        data = self.source.read(size)
        self.digest.update(data)
        return data


def archive_digest(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        while block := stream.read(CHUNK):
            digest.update(block)
    return digest.hexdigest()


@contextmanager
def tenant_lock(directory):
    import fcntl
    write_guard()
    fd = os.open(directory / '.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'rb') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SnapshotError('already_running') from None
        yield


def sync_directory(directory):
    write_guard()
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def backup_tenant(tenant_id):
    tenant_id = int(tenant_id)
    if not eligible(tenant_id):
        return None
    run = BackupRun.objects.create(tenant_id=tenant_id)
    temporary = None
    try:
        with pinned_root() as root:
            directory = root / f'tenant-{tenant_id}'
            write_guard()
            if directory.is_symlink():
                raise SnapshotError('unsafe_destination')
            directory.mkdir(mode=0o700, exist_ok=True)
            write_guard()
            os.chmod(directory, 0o700)
            with tenant_lock(directory):
                BackupRun.objects.filter(tenant_id=tenant_id, status='running').exclude(pk=run.pk).update(
                    status='failed', error_code='worker_interrupted', finished_at=timezone.now(),
                )
                if not eligible(tenant_id):
                    raise SnapshotError('subscription_inactive')
                # A previous worker may have died mid-transfer; encrypted partials
                # are safe to remove only while holding this tenant's lock.
                for stale in directory.glob('*.partial'):
                    write_guard()
                    stale.unlink()
                name = f'{timezone.now():%Y%m%dT%H%M%S}-{uuid.uuid4().hex}.cvb'
                temporary = directory / f'{name}.partial'
                write_guard()
                fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
                with os.fdopen(fd, 'wb') as output:
                    writer = EncryptWriter(output, write_guard)
                    with consistent_read():
                        fixture, files = collect(tenant_id)
                    members = {'fixture.json': hashlib.sha256(fixture).hexdigest()}
                    with tarfile.open(fileobj=writer, mode='w|gz') as tar:
                        add_bytes(tar, 'fixture.json', fixture)
                        for file in files:
                            path = media_path(file)
                            # Missing/changed source files fail the whole snapshot.
                            with open(path, 'rb') as source:
                                before = os.fstat(source.fileno())
                                info = tarfile.TarInfo('media/' + file)
                                info.size, info.mode = before.st_size, 0o600
                                reader = DigestReader(source)
                                tar.addfile(info, reader)
                                after = os.fstat(source.fileno())
                                if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                                    raise SnapshotError('source_changed')
                                members[info.name] = reader.digest.hexdigest()
                        add_bytes(tar, 'manifest.json', json.dumps({
                            'version': 1, 'tenant_id': tenant_id,
                            'created_at': timezone.now().isoformat(), 'members': members,
                        }).encode())
                    writer.finish()
                    write_guard()
                    output.flush()
                    os.fsync(output.fileno())
                verify(temporary, tenant_id)
                if not eligible(tenant_id):
                    raise SnapshotError('subscription_inactive')
                final = directory / name
                write_guard()
                os.replace(temporary, final)
                temporary = None
                sync_directory(directory)
                run.archive_name = name
                run.size_bytes = final.stat().st_size
                run.sha256 = archive_digest(final)
                run.verified_at = timezone.now()
                run.recovery_status = 'integrity_verified'
                run.status = 'success'
                # Keep at least two versions and seven days. No cleanup for inactive
                # tenants, and never delete data from the original media/database.
                versions = sorted(directory.glob('*.cvb'), key=lambda p: (p.stat().st_mtime_ns, p.name), reverse=True)
                keep = max(2, settings.CLOUD_BACKUP_KEEP_VERSIONS)
                cutoff = (timezone.now() - timedelta(days=7)).timestamp()
                for old in versions[keep:]:
                    if old.stat().st_mtime < cutoff and eligible(tenant_id):
                        write_guard()
                        old.unlink()
                run.retained_bytes = sum(p.stat().st_size for p in directory.glob('*.cvb'))
    except Exception as exc:
        # Never persist exception text: it may contain SQL, credentials or paths.
        run.status = 'failed'
        if isinstance(exc, SnapshotError):
            run.error_code = str(exc) if str(exc).replace('_', '').isalnum() else 'snapshot_failed'
        elif isinstance(exc, OSError) and exc.errno == errno.ENOSPC:
            run.error_code = 'insufficient_space'
        else:
            run.error_code = 'backup_failed'
    finally:
        run.finished_at = timezone.now()
        run.save()
    return run
