import base64
import errno
import json
import os
import tempfile
from contextlib import ExitStack, contextmanager, nullcontext
from pathlib import Path
from unittest.mock import patch
from unittest import skipUnless

from django.conf import settings
from django.core.management import call_command
from django.test import TransactionTestCase
from django.utils import timezone

from apps.auth.models import CarWash, CarWashFeaturePurchase, SupportTicket, SupportTicketAttachment, User
from apps.inventory.models import ExpenseEntry
from apps.vehicles.models import VehicleEntry
from apps.subscriptions.models import PlatformProject, ServiceProduct, ServicePlan, ServiceSubscription, ServicePeriod
from .archive import restore_fixture, verify
from .models import BackupRun
from .service import backup_tenant, mount_guard
from .snapshot import SnapshotError, collect


class CloudBackupTests(TransactionTestCase):
    databases = {'default', 'recovery'} if 'recovery' in settings.DATABASES else {'default'}

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.disk, self.media = self.root / 'disk', self.root / 'media'
        self.disk.mkdir()
        self.media.mkdir()
        self.key = self.root / 'key'
        self.key.write_bytes(base64.b64encode(os.urandom(32)))
        os.chmod(self.key, 0o600)
        self.settings_override = self.settings(
            CLOUD_BACKUP_ROOT=str(self.disk), CLOUD_BACKUP_KEY_FILE=str(self.key),
            CLOUD_BACKUP_MIN_FREE_BYTES=0, MEDIA_ROOT=str(self.media),
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        @contextmanager
        def pin():
            yield self.disk
        # Windows has no Linux mount namespace/flock. Only OS boundaries are
        # stubbed; real encryption, filesystem IO, ORM and restore run below.
        self.stack.enter_context(patch('apps.cloud_backup.service.pinned_root', pin))
        self.stack.enter_context(patch('apps.cloud_backup.service.mount_guard'))
        self.stack.enter_context(patch('apps.cloud_backup.service.tenant_lock', lambda _: nullcontext()))
        self.stack.enter_context(patch('apps.cloud_backup.service.sync_directory'))
        self.a = CarWash.objects.create(name='A', slug='backup-a')
        self.b = CarWash.objects.create(name='B', slug='backup-b')
        self.user = User.objects.create_user(username='backup-a', tenant=self.a)
        CarWashFeaturePurchase.objects.create(tenant=self.a, feature_key='cloud_storage', is_active=True)
        self.ticket = SupportTicket.objects.create(tenant=self.a, created_by=self.user, subject='A private')
        (self.media / 'a.txt').write_bytes(b'A PRIVATE MEDIA')
        (self.media / 'b.txt').write_bytes(b'B PRIVATE MEDIA')
        SupportTicketAttachment.objects.create(ticket=self.ticket, file='a.txt', uploaded_by=self.user)
        ExpenseEntry.objects.create(tenant=self.b, title='B private', amount=1, attachment='b.txt')

    def archive(self, run):
        return self.disk / f'tenant-{self.a.pk}' / run.archive_name

    @skipUnless('recovery' in settings.DATABASES, 'Use apps.cloud_backup.test_settings for actual database recovery tests')
    def test_scope_media_encryption_and_recovery(self):
        run = backup_tenant(self.a.pk)
        self.assertEqual(run.status, 'success', run.error_code)
        archive = self.archive(run)
        self.assertNotIn(b'A PRIVATE MEDIA', archive.read_bytes())
        output = self.root / 'recovered'
        call_command('recover_cloud_backup', str(archive), tenant=self.a.pk, output=str(output), database='recovery')
        self.assertEqual((output / 'media/a.txt').read_bytes(), b'A PRIVATE MEDIA')
        self.assertFalse((output / 'media/b.txt').exists())
        restored = SupportTicketAttachment.objects.using('recovery').get()
        self.assertEqual(restored.ticket.tenant_id, self.a.pk)
        self.assertEqual(restored.uploaded_by.username, self.user.username)
        self.assertFalse(CarWash.objects.using('recovery').filter(pk=self.b.pk).exists())
        self.assertGreater(run.retained_bytes, 0)
        self.assertIsNotNone(run.verified_at)

    def test_ineligible_does_not_create_directory_or_run(self):
        self.assertIsNone(backup_tenant(self.b.pk))
        self.assertFalse((self.disk / f'tenant-{self.b.pk}').exists())
        self.assertFalse(BackupRun.objects.exists())

    def test_cross_tenant_relation_fails_closed(self):
        other = User.objects.create_user(username='other', tenant=self.b)
        self.ticket.created_by = other
        self.ticket.save()
        run = backup_tenant(self.a.pk)
        self.assertEqual(run.error_code, 'foreign_tenant_relation')
        self.assertFalse(list(self.disk.rglob('*.cvb')))

    def test_mount_missing_never_creates_destination(self):
        with patch('apps.cloud_backup.service.mount_guard', side_effect=SnapshotError('mount_unavailable')):
            run = backup_tenant(self.a.pk)
        self.assertEqual(run.error_code, 'mount_unavailable')
        self.assertFalse(list(self.disk.iterdir()))

    def test_low_space_and_enospc(self):
        with patch('apps.cloud_backup.service.shutil.disk_usage') as usage:
            usage.return_value.free = -1
            run = backup_tenant(self.a.pk)
        self.assertEqual(run.error_code, 'insufficient_space')
        with patch('apps.cloud_backup.service.EncryptWriter.write', side_effect=OSError(errno.ENOSPC, 'secret')):
            run = backup_tenant(self.a.pk)
        self.assertEqual(run.error_code, 'insufficient_space')
        self.assertNotIn('secret', run.error_code)
        self.assertFalse(list(self.disk.rglob('*.cvb')))

    def test_disconnect_mid_transfer_preserves_previous_success(self):
        first = backup_tenant(self.a.pk)
        original = self.archive(first).read_bytes()
        with patch('apps.cloud_backup.service.EncryptWriter.write', side_effect=SnapshotError('mount_unavailable')):
            failed = backup_tenant(self.a.pk)
        self.assertEqual(failed.status, 'failed')
        self.assertEqual(self.archive(first).read_bytes(), original)
        retried = backup_tenant(self.a.pk)
        self.assertEqual(retried.status, 'success', retried.error_code)
        self.assertFalse(list(self.disk.rglob('*.partial')))

    def test_tamper_truncate_wrong_tenant_and_live_restore_rejected(self):
        run = backup_tenant(self.a.pk)
        archive = self.archive(run)
        with self.assertRaises(SnapshotError):
            verify(archive, self.b.pk)
        raw = archive.read_bytes()
        for data in (raw[:-8], raw[:50] + bytes([raw[50] ^ 1]) + raw[51:]):
            corrupt = self.root / 'corrupt'
            corrupt.write_bytes(data)
            with self.assertRaises(Exception):
                verify(corrupt, self.a.pk)
        with self.assertRaises(SnapshotError):
            restore_fixture(self.root / 'unused', self.a.pk, 'default')

    def test_disabled_subscription_preserves_archives(self):
        run = backup_tenant(self.a.pk)
        CarWashFeaturePurchase.objects.filter(tenant=self.a).update(is_active=False)
        self.assertIsNone(backup_tenant(self.a.pk))
        self.assertTrue(self.archive(run).exists())

    def test_missing_media_and_path_traversal_fail_closed(self):
        (self.media / 'a.txt').unlink()
        self.assertEqual(backup_tenant(self.a.pk).status, 'failed')
        SupportTicketAttachment.objects.filter(ticket=self.ticket).update(file='../secret')
        self.assertEqual(backup_tenant(self.a.pk).error_code, 'unsafe_path')

    def test_ai_images_are_scoped_by_sidecar_tenant(self):
        audit = self.media / 'ai_plate_audit/2026/10/26'
        audit.mkdir(parents=True)
        for tenant in (self.a, self.b):
            vehicle = VehicleEntry.objects.create(tenant=tenant, plate_number=f'plate-{tenant.pk}')
            image = audit / f'vehicle-{vehicle.pk}-test.jpg'
            image.write_bytes(f'private-{tenant.pk}'.encode())
            image.with_suffix('.json').write_text(json.dumps({
                'tenant_id': tenant.pk, 'vehicle_id': vehicle.pk,
                'image_path': image.relative_to(self.media).as_posix(),
            }))
        fixture, files = collect(self.a.pk)
        self.assertEqual(len([p for p in files if p.endswith('.jpg')]), 1)
        run = backup_tenant(self.a.pk)
        self.assertEqual(run.status, 'success', run.error_code)
        verify(self.archive(run), self.a.pk)

    @skipUnless('recovery' in settings.DATABASES, 'Use apps.cloud_backup.test_settings for actual database recovery tests')
    def test_shared_catalog_and_indirect_subscription_children_restore(self):
        project = PlatformProject.objects.create(code='backup-test', name='shared')
        product = ServiceProduct.objects.create(project=project, product_key='cloud_storage', title='cloud')
        plan = ServicePlan.objects.create(product=product, code='annual', title='annual', billing_cycle='annual')
        sub = ServiceSubscription.objects.create(tenant=self.a, project=project, product=product, plan=plan)
        ServicePeriod.objects.create(subscription=sub, plan=plan, starts_at=timezone.now())
        other = ServiceSubscription.objects.create(tenant=self.b, project=project, product=product, plan=plan)
        ServicePeriod.objects.create(subscription=other, plan=plan, starts_at=timezone.now())
        run = backup_tenant(self.a.pk)
        self.assertEqual(run.status, 'success', run.error_code)
        output = self.root / 'restore-catalog'
        call_command('recover_cloud_backup', str(self.archive(run)), tenant=self.a.pk, output=str(output), database='recovery')
        restored = ServicePeriod.objects.using('recovery').get()
        self.assertEqual(restored.subscription.tenant_id, self.a.pk)
        self.assertEqual(restored.plan.product.project.code, 'backup-test')

    def test_shared_media_across_models_fails_closed(self):
        ExpenseEntry.objects.filter(tenant=self.b).update(attachment='a.txt')
        self.assertEqual(backup_tenant(self.a.pk).error_code, 'shared_media')

    def test_verification_failure_does_not_publish_snapshot(self):
        with patch('apps.cloud_backup.service.verify', side_effect=SnapshotError('checksum_mismatch')):
            run = backup_tenant(self.a.pk)
        self.assertEqual(run.error_code, 'checksum_mismatch')
        self.assertFalse(list(self.disk.rglob('*.cvb')))

    def test_retention_keeps_two_and_never_touches_source(self):
        with self.settings(CLOUD_BACKUP_KEEP_VERSIONS=2):
            for _ in range(3):
                run = backup_tenant(self.a.pk)
                self.assertEqual(run.status, 'success', run.error_code)
                os.utime(self.archive(run), (1, 1))
            self.assertEqual(len(list(self.disk.rglob('*.cvb'))), 2)
            self.assertTrue((self.media / 'a.txt').exists())

    def test_host_mount_record_is_mandatory(self):
        # Invoke the actual guard, bypassing only Linux stat on this Windows host.
        info = self.root / 'mountinfo'
        info.write_text('1 0 8:17 / /mnt/extra-storage rw - ext4 /dev/sdb1 rw\n')
        with self.settings(CLOUD_BACKUP_ROOT='/mnt/extra-storage', CLOUD_BACKUP_DEVICE='8:17', CLOUD_BACKUP_HOST_MOUNTINFO=str(info)):
            with patch('pathlib.Path.is_absolute', return_value=True), patch('pathlib.Path.resolve', return_value=Path('/mnt/extra-storage')), patch('pathlib.Path.stat') as stat, patch('pathlib.Path.is_mount', return_value=True), patch('os.major', return_value=8, create=True), patch('os.minor', return_value=17, create=True):
                stat.return_value.st_dev = 1
                # On Windows Path renders backslashes; use a native-path record.
                info.write_text(f'1 0 8:17 / {Path("/mnt/extra-storage")} rw - ext4 /dev/sdb1 rw\n')
                mount_guard()
                info.write_text('1 0 8:1 / / rw - ext4 /dev/sda1 rw\n')
                with self.assertRaises(SnapshotError):
                    mount_guard()
