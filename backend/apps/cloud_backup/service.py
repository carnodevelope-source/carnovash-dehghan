import errno
import hashlib
import json
import os
import shutil
import stat
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
from .snapshot import SnapshotError, add_bytes, collect, open_media, fingerprint


def eligible(tenant_id):
    return CarWashFeaturePurchase.objects.filter(
        tenant_id=tenant_id, feature_key='cloud_storage', is_active=True,
    ).exists()


def mount_guard():
    root = Path(settings.CLOUD_BACKUP_MOUNT)
    expected = settings.CLOUD_BACKUP_DEVICE
    if not expected or not root.is_absolute() or str(root.resolve()) != str(root):
        raise SnapshotError('mount_unavailable')
    try:
        mount_stat = root.stat()
        device = f'{os.major(mount_stat.st_dev)}:{os.minor(mount_stat.st_dev)}'
        records = Path(settings.CLOUD_BACKUP_HOST_MOUNTINFO).read_text().splitlines()
        def valid_record(line):
            parts = line.split()
            if len(parts) < 10 or '-' not in parts:
                return False
            split = parts.index('-')
            return (parts[2] == expected and parts[3] == '/' and parts[4] == str(root)
                    and 'rw' in parts[5].split(',') and parts[split + 1] == 'ext4')
        host_mounted = any(valid_record(line) for line in records)
        if not root.is_mount() or device != expected or not host_mounted:
            raise SnapshotError('mount_unavailable')
    except OSError:
        raise SnapshotError('mount_unavailable') from None


@contextmanager
def pinned_root():
    # Every write resolves via this open directory, so an unmount race can never
    # redirect writes to the SSD directory hidden underneath the mount.
    mount_guard()
    mount = Path(settings.CLOUD_BACKUP_MOUNT)
    destination = Path(settings.CLOUD_BACKUP_ROOT)
    if destination != mount / 'cloud-backups':
        raise SnapshotError('unsafe_destination')
    mount_fd = os.open(mount, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    fd = None
    try:
        fd = os.open('cloud-backups', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=mount_fd)
        mount_guard()
        actual = os.fstat(fd)
        if actual.st_dev != os.fstat(mount_fd).st_dev or actual.st_dev != os.stat(mount).st_dev:
            raise SnapshotError('mount_unavailable')
        if actual.st_uid != os.geteuid() or stat.S_IMODE(actual.st_mode) != 0o700:
            raise SnapshotError('unsafe_destination_permissions')
        if not os.access(f'/proc/self/fd/{fd}', os.R_OK | os.W_OK | os.X_OK):
            raise SnapshotError('destination_not_writable')
        yield Path(f'/proc/self/fd/{fd}')
    finally:
        if fd is not None:
            os.close(fd)
        os.close(mount_fd)


@contextmanager
def pinned_tenant(directory):
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise SnapshotError('unsafe_destination_permissions')
        yield Path(f'/proc/self/fd/{fd}')
    finally:
        os.close(fd)


def write_guard():
    mount_guard()
    if shutil.disk_usage(settings.CLOUD_BACKUP_MOUNT).free < settings.CLOUD_BACKUP_MIN_FREE_BYTES:
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
        info = os.fstat(lock.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.geteuid():
            raise SnapshotError('unsafe_destination')
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


def due(tenant_id):
    now = timezone.now()
    latest = BackupRun.objects.filter(tenant_id=tenant_id).order_by('-started_at').first()
    success = BackupRun.objects.filter(tenant_id=tenant_id, status='success').order_by('-finished_at').first()
    if success and success.finished_at and (now - success.finished_at).total_seconds() < max(60, settings.CLOUD_BACKUP_INTERVAL_SECONDS):
        return False
    if latest and latest.status in {'failed', 'running'}:
        previous_success = success.started_at if success else None
        failures = BackupRun.objects.filter(tenant_id=tenant_id, status='failed')
        if previous_success:
            failures = failures.filter(started_at__gt=previous_success)
        failure_count = len(list(failures.values_list('pk', flat=True)[:9]))
        wait = min(21600, 60 * 2 ** failure_count)
        if (now - (latest.finished_at or latest.started_at)).total_seconds() < wait:
            return False
    return True


def backup_tenant(tenant_id, *, scheduled=False):
    tenant_id = int(tenant_id)
    if not eligible(tenant_id):
        return None
    run = None
    temporary = None
    try:
        with pinned_root() as root:
            directory = root / f'tenant-{tenant_id}'
            write_guard()
            if directory.is_symlink():
                raise SnapshotError('unsafe_destination')
            directory.mkdir(mode=0o700, exist_ok=True)
            with pinned_tenant(directory) as directory, tenant_lock(directory):
                if scheduled and not due(tenant_id):
                    return None
                BackupRun.objects.filter(tenant_id=tenant_id, status='running').update(
                    status='failed', error_code='worker_interrupted', finished_at=timezone.now(),
                )
                run = BackupRun.objects.create(tenant_id=tenant_id)
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
                            # Missing/changed source files fail the whole snapshot.
                            with open_media(file) as source:
                                before = os.fstat(source.fileno())
                                if fingerprint(before) != files.fingerprints[file]:
                                    raise SnapshotError('source_changed')
                                info = tarfile.TarInfo('media/' + file)
                                info.size, info.mode = before.st_size, 0o600
                                reader = DigestReader(source)
                                tar.addfile(info, reader)
                                after = os.fstat(source.fileno())
                                if fingerprint(before) != fingerprint(after):
                                    raise SnapshotError('source_changed')
                                if file in files.digests and reader.digest.hexdigest() != files.digests[file]:
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
        if isinstance(exc, SnapshotError) and str(exc) == 'already_running':
            return None
        if run is None:
            run = BackupRun.objects.create(tenant_id=tenant_id)
        # Never persist exception text: it may contain SQL, credentials or paths.
        run.status = 'failed'
        if isinstance(exc, SnapshotError):
            run.error_code = str(exc) if str(exc).replace('_', '').isalnum() else 'snapshot_failed'
        elif isinstance(exc, OSError) and exc.errno == errno.ENOSPC:
            run.error_code = 'insufficient_space'
        elif isinstance(exc, OSError) and exc.errno in {errno.EIO, errno.EROFS}:
            run.error_code = 'storage_io_error' if exc.errno == errno.EIO else 'storage_read_only'
        elif isinstance(exc, PermissionError):
            run.error_code = 'storage_permission_denied'
        else:
            run.error_code = 'backup_failed'
    finally:
        if run is not None:
            run.finished_at = timezone.now()
            run.save()
    return run
