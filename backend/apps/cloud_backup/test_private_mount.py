"""Real mount/unmount only in an opt-in, disposable Docker mount namespace.

No host devices or host writable paths are passed to this test container.
Production remains ext4-only. The private guard argument admits tmpfs solely
for this disposable mount test; all runtime calls retain the ext4 default.
"""
import os
import subprocess
import tempfile
from functools import partial
from pathlib import Path
from unittest import skipUnless
from unittest.mock import patch
from django.test import SimpleTestCase
from . import service
from .snapshot import SnapshotError


@skipUnless(os.environ.get('CARVASH_PRIVATE_MOUNT_TEST') == '1', 'Private Docker mount namespace opt-in required')
class PrivateMountTests(SimpleTestCase):
    def setUp(self):
        self.assertEqual(os.geteuid(), 0)
        self.tmp = tempfile.TemporaryDirectory(prefix='carvash-private-mount-', dir='/tmp')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'mounted'
        self.root.mkdir()
        subprocess.run(['mount','-t','tmpfs','-o','size=16m','tmpfs',str(self.root)],check=True,capture_output=True)
        self.addCleanup(self.unmount)
        (self.root/'cloud-backups').mkdir(mode=0o700)
        info=self.root.stat()
        self.device=f'{os.major(info.st_dev)}:{os.minor(info.st_dev)}'
        config=self.settings(CLOUD_BACKUP_MOUNT=str(self.root),CLOUD_BACKUP_ROOT=str(self.root/'cloud-backups'),
            CLOUD_BACKUP_DEVICE=self.device,CLOUD_BACKUP_HOST_MOUNTINFO='/proc/self/mountinfo',CLOUD_BACKUP_MIN_FREE_BYTES=0)
        config.enable()
        self.addCleanup(config.disable)
        self.guard=partial(service.mount_guard,_filesystem='tmpfs')

    def unmount(self):
        if self.root.is_mount():
            subprocess.run(['umount','-l',str(self.root)],check=True,capture_output=True)

    def test_actual_disconnect_refuses_writes_and_pins_original_filesystem(self):
        with patch.object(service,'mount_guard',self.guard):
            with service.pinned_root() as root:
                (root/'tenant-123').mkdir(mode=0o700)
                with service.pinned_tenant(root/'tenant-123') as tenant:
                    service.write_guard()
                    self.unmount()
                    (self.root/'cloud-backups').mkdir(mode=0o700)
                    with self.assertRaisesRegex(SnapshotError,'mount_unavailable'):
                        service.write_guard()
                    # FD still targets detached test RAM disk, never the exposed directory.
                    (tenant/'detached-probe').write_bytes(b'test')
                    self.assertFalse((self.root/'cloud-backups/tenant-123').exists())
            self.assertEqual(list((self.root/'cloud-backups').iterdir()),[])

    def test_real_readonly_remount_and_wrong_device_are_rejected(self):
        with patch.object(service,'mount_guard',self.guard):
            service.mount_guard()
            with self.settings(CLOUD_BACKUP_DEVICE='999:999'):
                with self.assertRaises(SnapshotError):
                    service.mount_guard()
            subprocess.run(['mount','-o','remount,ro',str(self.root)],check=True,capture_output=True)
            with self.assertRaises(SnapshotError):
                service.mount_guard()
            with self.assertRaises(OSError):
                (self.root/'cannot-write').write_bytes(b'test')
