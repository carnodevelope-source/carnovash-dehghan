"""Destructive-to-scratch-only tests. Run as root INSIDE a private mount namespace.

Never targets /mnt/extra-storage: every filesystem is a new /tmp ext4 loop image.
"""
import errno
import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest import skipUnless

from django.test import SimpleTestCase

from .service import mount_guard, pinned_root, pinned_tenant, tenant_lock, write_guard
from .snapshot import SnapshotError, open_media


@skipUnless(sys.platform == 'linux' and os.environ.get('CLOUD_BACKUP_LINUX_MOUNT_TESTS') == '1', 'Requires opt-in private Linux mount namespace')
class LinuxStorageTests(SimpleTestCase):
    def setUp(self):
        if os.geteuid() != 0 or os.readlink('/proc/self/ns/mnt') == os.readlink('/proc/1/ns/mnt'):
            self.fail('Run in an isolated root mount namespace, not the host namespace')
        self.temp = tempfile.TemporaryDirectory(prefix='carvash-backup-mount-test-', dir='/tmp')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        os.chmod(self.base, 0o755)
        self.mount = self.base / 'mount'
        self.mount.mkdir()
        self.image = self.base / 'scratch.ext4'
        with open(self.image, 'wb') as output:
            output.truncate(32 * 1024 * 1024)
        subprocess.run(['mkfs.ext4', '-q', '-F', str(self.image)], check=True, capture_output=True)
        subprocess.run(['mount', '-o', 'loop', str(self.image), str(self.mount)], check=True, capture_output=True)
        self.addCleanup(self.unmount)
        self.destination = self.mount / 'cloud-backups'
        self.destination.mkdir(mode=0o700)
        os.chown(self.destination, 10001, 10001)
        info = self.mount.stat()
        self.device = f'{os.major(info.st_dev)}:{os.minor(info.st_dev)}'
        override = self.settings(CLOUD_BACKUP_MOUNT=str(self.mount), CLOUD_BACKUP_ROOT=str(self.destination),
                                 CLOUD_BACKUP_DEVICE=self.device, CLOUD_BACKUP_HOST_MOUNTINFO='/proc/self/mountinfo',
                                 CLOUD_BACKUP_MIN_FREE_BYTES=0)
        override.enable()
        self.addCleanup(override.disable)

    def unmount(self):
        if self.mount.is_mount():
            subprocess.run(['umount', '-l', str(self.mount)], check=True, capture_output=True)

    @contextmanager
    def worker(self):
        old_uid, old_gid = os.geteuid(), os.getegid()
        os.setegid(10001)
        os.seteuid(10001)
        try:
            yield
        finally:
            os.seteuid(old_uid)
            os.setegid(old_gid)

    def test_real_uid_gid_can_write_only_private_destination(self):
        with self.worker():
            with pinned_root() as root:
                write_guard()
                (root / 'worker-probe').write_bytes(b'private test')
                self.assertEqual((root / 'worker-probe').stat().st_uid, 10001)
                with self.assertRaises(PermissionError):
                    (self.mount / 'outside').write_bytes(b'forbidden')
        self.assertEqual(self.destination.stat().st_mode & 0o777, 0o700)

    def test_device_mismatch_and_unmounted_directory_are_rejected(self):
        with self.settings(CLOUD_BACKUP_DEVICE='999:999'):
            with self.assertRaises(SnapshotError):
                mount_guard()
        self.unmount()
        self.destination.mkdir(mode=0o700)
        with self.assertRaises(SnapshotError):
            mount_guard()
        with self.worker():
            with self.assertRaises(SnapshotError):
                with pinned_root():
                    self.fail('Unmounted directory accepted')
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_lazy_unmount_pins_old_filesystem_never_underlying_directory(self):
        with self.worker():
            with pinned_root() as root:
                (root / 'tenant-1').mkdir(mode=0o700)
                with pinned_tenant(root / 'tenant-1') as tenant:
                    # Temporarily regain root only to detach our disposable mount.
                    os.seteuid(0)
                    self.unmount()
                    self.destination.mkdir(mode=0o700)
                    os.seteuid(10001)
                    with self.assertRaises(SnapshotError):
                        write_guard()
                    # Prove the FD itself still resolves to the old filesystem.
                    (tenant / 'detached-probe.partial').write_bytes(b'pinned')
                    self.assertFalse((self.destination / 'tenant-1').exists())
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_real_flock_blocks_second_process(self):
        with self.worker():
            with pinned_root() as root:
                (root / 'tenant-1').mkdir(mode=0o700)
                with pinned_tenant(root / 'tenant-1') as tenant, tenant_lock(tenant):
                    # Separate open descriptions in the same process also conflict.
                    with self.assertRaisesRegex(SnapshotError, 'already_running'):
                        with tenant_lock(tenant):
                            self.fail('Concurrent lock acquired')
                    lock_path = self.destination / 'tenant-1/.lock'
                    script = 'import fcntl,sys; f=open(sys.argv[1], "rb"); fcntl.flock(f, fcntl.LOCK_EX|fcntl.LOCK_NB)'
                    result = subprocess.run(['/usr/bin/python3', '-c', script, str(lock_path)], capture_output=True)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(b'BlockingIOError', result.stderr)

    def test_destination_tenant_and_source_symlinks_are_rejected(self):
        with self.worker():
            with pinned_root() as root:
                (root / 'tenant-1').symlink_to(self.base)
                with self.assertRaises(OSError):
                    with pinned_tenant(root / 'tenant-1'):
                        self.fail('Tenant symlink accepted')
        media = self.base / 'media'
        media.mkdir()
        (media / 'outside').symlink_to('/etc/passwd')
        with self.settings(MEDIA_ROOT=str(media)):
            with self.assertRaises(SnapshotError):
                with open_media('outside'):
                    self.fail('Media symlink accepted')

    def test_low_space_readonly_and_permission_mismatch(self):
        with self.worker():
            with self.settings(CLOUD_BACKUP_MIN_FREE_BYTES=2 ** 60):
                with self.assertRaisesRegex(SnapshotError, 'insufficient_space'):
                    write_guard()
        os.chmod(self.destination, 0o755)
        with self.worker():
            with self.assertRaisesRegex(SnapshotError, 'unsafe_destination_permissions'):
                with pinned_root():
                    self.fail('Unsafe permissions accepted')
        os.chmod(self.destination, 0o700)
        subprocess.run(['mount', '-o', 'remount,ro', str(self.mount)], check=True, capture_output=True)
        with self.assertRaises(SnapshotError):
            mount_guard()
        with self.worker():
            with self.assertRaises(OSError) as raised:
                (self.destination / 'readonly-probe').write_bytes(b'test')
            self.assertEqual(raised.exception.errno, errno.EROFS)
