import base64
import errno
import hashlib
import io
import json
import os
import struct
import tarfile
import tempfile
from contextlib import ExitStack, contextmanager, nullcontext
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from unittest import skipUnless

from django.conf import settings
from django.core.management import call_command
from django.test import TransactionTestCase
from django.utils import timezone

from apps.auth.models import CarWash, CarWashFeaturePurchase, SupportTicket, SupportTicketAttachment, SupportTicketMessage, User
from apps.inventory.models import ExpenseEntry
from apps.vehicles.models import CustomerProfile, VehicleEntry
from apps.vehicles.tests.guard_support import seed_legacy_vehicles
from apps.subscriptions.models import PlatformProject, ServiceProduct, ServicePlan, ServiceSubscription, ServicePeriod
from .archive import restore_fixture, verify, EncryptWriter, DecryptReader, archive_cipher, MAGIC, CHUNK
from .models import BackupRun
from .service import backup_tenant, mount_guard, due
from .snapshot import SnapshotError, collect, ownership_registry, add_bytes, serialize_row


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
            CLOUD_BACKUP_ROOT=str(self.disk), CLOUD_BACKUP_MOUNT=str(self.disk), CLOUD_BACKUP_KEY_FILE=str(self.key),
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
        self.stack.enter_context(patch('apps.cloud_backup.service.pinned_tenant', lambda path: nullcontext(path)))
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
        call_command('recover_cloud_backup', str(archive), tenant=self.a.pk, output=str(output), database='recovery', confirm_isolated_restore=True)
        self.assertEqual((output / 'media/a.txt').read_bytes(), b'A PRIVATE MEDIA')
        self.assertFalse((output / 'media/b.txt').exists())
        restored = SupportTicketAttachment.objects.using('recovery').get()
        self.assertEqual(restored.ticket.tenant_id, self.a.pk)
        self.assertEqual(restored.uploaded_by.username, self.user.username)
        self.assertFalse(CarWash.objects.using('recovery').filter(pk=self.b.pk).exists())
        self.assertGreater(run.retained_bytes, 0)
        self.assertIsNotNone(run.verified_at)
        from django.apps import apps
        for expected in json.loads((output / 'fixture.json').read_text()):
            obj = apps.get_model(expected['model']).objects.using('recovery').get(pk=expected['pk'])
            actual = json.loads(serialize_row(obj))[0]
            if expected['model'] == 'cw_auth.user':
                actual['fields'].update(groups=[], user_permissions=[])
            self.assertEqual(actual, expected)

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
        call_command('recover_cloud_backup', str(self.archive(run)), tenant=self.a.pk, output=str(output), database='recovery', confirm_isolated_restore=True)
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
        with self.settings(CLOUD_BACKUP_MOUNT='/mnt/extra-storage', CLOUD_BACKUP_DEVICE='8:17', CLOUD_BACKUP_HOST_MOUNTINFO=str(info)):
            with patch('pathlib.Path.is_absolute', return_value=True), patch('pathlib.Path.resolve', return_value=Path('/mnt/extra-storage')), patch('pathlib.Path.stat') as stat, patch('pathlib.Path.is_mount', return_value=True), patch('os.major', return_value=8, create=True), patch('os.minor', return_value=17, create=True):
                stat.return_value.st_dev = 1
                # On Windows Path renders backslashes; use a native-path record.
                info.write_text(f'1 0 8:17 / {Path("/mnt/extra-storage")} rw - ext4 /dev/sdb1 rw\n')
                mount_guard()
                info.write_text('1 0 8:1 / / rw - ext4 /dev/sda1 rw\n')
                with self.assertRaises(SnapshotError):
                    mount_guard()

    def test_every_first_party_model_has_reviewed_ownership(self):
        from django.apps import apps
        registry = ownership_registry()
        actual = {m._meta.label_lower for m in apps.get_models() if m._meta.app_config.name.startswith('apps.')}
        self.assertEqual(set(registry), actual)

    def test_unknown_model_is_rejected_even_with_tenant(self):
        from django.apps import apps
        from types import SimpleNamespace
        unknown = SimpleNamespace(_meta=SimpleNamespace(label_lower='inventory.new_private_model', app_config=SimpleNamespace(name='apps.inventory')))
        with patch('apps.cloud_backup.snapshot.apps.get_models', return_value=[*apps.get_models(), unknown]):
            with self.assertRaisesRegex(SnapshotError, 'unclassified_model'):
                ownership_registry()

    def test_snapshot_limits_fail_without_final_archive(self):
        with self.settings(CLOUD_BACKUP_MAX_ROWS=1):
            self.assertEqual(backup_tenant(self.a.pk).error_code, 'snapshot_limit_exceeded')
        with self.settings(CLOUD_BACKUP_MAX_JSON_BYTES=32):
            self.assertEqual(backup_tenant(self.a.pk).error_code, 'snapshot_limit_exceeded')
        with self.settings(CLOUD_BACKUP_MAX_FILES=0):
            self.assertEqual(backup_tenant(self.a.pk).error_code, 'snapshot_limit_exceeded')
        self.assertFalse(list(self.disk.rglob('*.cvb')))

    def test_changed_file_after_snapshot_is_rejected(self):
        def collect_then_change(tenant):
            result = collect(tenant)
            (self.media / 'a.txt').write_bytes(b'CHANGED')
            return result
        with patch('apps.cloud_backup.service.collect', side_effect=collect_then_change):
            self.assertEqual(backup_tenant(self.a.pk).error_code, 'source_changed')
        self.assertFalse(list(self.disk.rglob('*.cvb')))

    def test_eio_and_readonly_preserve_success_and_redact_errors(self):
        first = backup_tenant(self.a.pk)
        for error, code in ((errno.EIO, 'storage_io_error'), (errno.EROFS, 'storage_read_only')):
            with patch('apps.cloud_backup.service.EncryptWriter.write', side_effect=OSError(error, 'private-secret')):
                run = backup_tenant(self.a.pk)
            self.assertEqual(run.error_code, code)
            self.assertTrue(self.archive(first).exists())
            self.assertFalse(run.archive_name)

    def test_scheduled_run_checks_interval_inside_lock(self):
        self.assertTrue(due(self.a.pk))
        first = backup_tenant(self.a.pk, scheduled=True)
        self.assertEqual(first.status, 'success')
        self.assertFalse(due(self.a.pk))
        self.assertIsNone(backup_tenant(self.a.pk, scheduled=True))
        self.assertEqual(BackupRun.objects.count(), 1)

    def test_failure_backoff_and_busy_lock(self):
        with patch('apps.cloud_backup.service.EncryptWriter.write', side_effect=OSError(errno.EIO, 'error')):
            backup_tenant(self.a.pk)
        self.assertFalse(due(self.a.pk))
        with patch('apps.cloud_backup.service.tenant_lock', side_effect=SnapshotError('already_running')):
            self.assertIsNone(backup_tenant(self.a.pk))
        self.assertEqual(BackupRun.objects.count(), 1)

    def test_v2_key_rotation_and_v1_recovery(self):
        old = backup_tenant(self.a.pk)
        with open(self.archive(old), 'rb') as source, io.BufferedReader(DecryptReader(source)) as stream:
            plaintext = stream.read()
        salt = os.urandom(32)
        cipher = archive_cipher(salt, legacy=True)
        legacy = self.root / 'legacy.cvb'
        with open(legacy, 'wb') as output:
            output.write(MAGIC + salt)
            blocks = [plaintext[i:i+CHUNK] for i in range(0, len(plaintext), CHUNK)] + [b'']
            for index, block in enumerate(blocks):
                encrypted = cipher.encrypt(index.to_bytes(12, 'big'), block, MAGIC)
                output.write(struct.pack('>I', len(encrypted)) + encrypted)
        ring = self.root / 'keyring'
        ring.write_text(json.dumps({
            'primary': self.key.read_text().strip(), 'legacy-v1': self.key.read_text().strip(),
            'rotated': base64.b64encode(os.urandom(32)).decode(),
        }))
        os.chmod(ring, 0o600)
        with self.settings(CLOUD_BACKUP_KEYRING_FILE=str(ring), CLOUD_BACKUP_KEY_ID='rotated'):
            new = backup_tenant(self.a.pk)
            self.assertEqual(new.status, 'success', new.error_code)
            for archive in (legacy, self.archive(old), self.archive(new)):
                verify(archive, self.a.pk)
        with self.settings(CLOUD_BACKUP_KEY_ID='unknown'):
            with self.assertRaises(SnapshotError):
                verify(self.archive(old), self.a.pk)

    def forged_archive(self, members):
        path = self.root / 'forged.cvb'
        with open(path, 'wb') as source:
            writer = EncryptWriter(source, lambda: None)
            with tarfile.open(fileobj=writer, mode='w|gz') as tar:
                for name, data in members:
                    add_bytes(tar, name, data)
            writer.finish()
        return path

    def test_authenticated_archive_rejects_traversal_duplicate_and_foreign_fixture(self):
        for members in ([('../escape', b'x')], [('fixture.json', b'[]'), ('fixture.json', b'[]')]):
            with self.assertRaises(SnapshotError):
                verify(self.forged_archive(members), self.a.pk)
        fixture, _ = collect(self.a.pk)
        rows = json.loads(fixture)
        rows.append({'model': 'cw_auth.carwash', 'pk': self.b.pk, 'fields': {'name': 'B'}})
        payload = json.dumps(rows).encode()
        manifest = json.dumps({'version': 1, 'tenant_id': self.a.pk, 'members': {'fixture.json': hashlib.sha256(payload).hexdigest()}}).encode()
        with self.assertRaises(SnapshotError):
            verify(self.forged_archive([('fixture.json', payload), ('manifest.json', manifest)]), self.a.pk)

    def test_restore_requires_explicit_approval_before_any_output(self):
        from django.core.management.base import CommandError
        run = backup_tenant(self.a.pk)
        output = self.root / 'not-created'
        with self.assertRaises(CommandError):
            call_command('recover_cloud_backup', str(self.archive(run)), tenant=self.a.pk, output=str(output), database='recovery')
        self.assertFalse(output.exists())

    def test_restore_rejects_existing_directory_and_corruption_before_output(self):
        from django.core.management.base import CommandError
        run = backup_tenant(self.a.pk)
        output = self.root / 'exists'
        output.mkdir()
        with self.assertRaises(CommandError):
            call_command('recover_cloud_backup', str(self.archive(run)), tenant=self.a.pk, output=str(output))
        archive = self.archive(run)
        archive.write_bytes(archive.read_bytes()[:-20])
        output = self.root / 'not-created'
        with self.assertRaises(CommandError):
            call_command('recover_cloud_backup', str(archive), tenant=self.a.pk, output=str(output))
        self.assertFalse(output.exists())

    @skipUnless(settings.DATABASES['default']['ENGINE'].endswith('mysql'), 'MySQL-only least-privilege integration test')
    def test_mysql_snapshot_with_only_generated_table_grants(self):
        from django.db import connection, DatabaseError
        password = os.urandom(24).hex()
        account = 'cloud_backup_test_limited'
        sql = io.StringIO()
        call_command('cloud_backup_grants', database_name=connection.settings_dict['NAME'], user=account, stdout=sql)
        with connection.cursor() as cursor:
            cursor.execute('CREATE USER %s@%s IDENTIFIED BY %s', [account, '%', password])
            for line in sql.getvalue().splitlines():
                cursor.execute(line)
        original = {k: connection.settings_dict[k] for k in ('USER', 'PASSWORD')}
        connection.close()
        connection.settings_dict.update(USER=account, PASSWORD=password)
        try:
            run = backup_tenant(self.a.pk)
            self.assertEqual(run.status, 'success', run.error_code)
            with self.assertRaises(DatabaseError):
                CarWash.objects.filter(pk=-1).update(name='not-written')
            with self.assertRaises(DatabaseError):
                BackupRun.objects.filter(pk=-1).delete()
            with connection.cursor() as cursor:
                with self.assertRaises(DatabaseError):
                    cursor.execute('CREATE TABLE cloud_backup_forbidden (id INT)')
        finally:
            connection.close()
            connection.settings_dict.update(original)
            with connection.cursor() as cursor:
                cursor.execute(f"DROP USER '{account}'@'%'")

    def test_authenticated_but_truncated_gzip_is_rejected(self):
        first = backup_tenant(self.a.pk)
        with open(self.archive(first), 'rb') as source, io.BufferedReader(DecryptReader(source)) as stream:
            compressed = stream.read()
        broken = self.root / 'truncated-gzip.cvb'
        with open(broken, 'wb') as output:
            writer = EncryptWriter(output, lambda: None)
            writer.write(compressed[:-8])  # All content present, but gzip CRC/length trailer missing.
            writer.finish()
        with self.assertRaises(Exception):
            verify(broken, self.a.pk)

    def test_generated_grants_exclude_technical_tables_and_writes(self):
        output = io.StringIO()
        call_command('cloud_backup_grants', database_name='review', stdout=output)
        statements = output.getvalue()
        self.assertIn('SELECT, INSERT, UPDATE ON `review`.`cloud_backup_backuprun`', statements)
        for forbidden in ('DELETE', 'CREATE', 'ALL PRIVILEGES', 'realtime_', 'django_session', 'bulkservicejob', 'auth_permission'):
            self.assertNotIn(forbidden, statements)

    @skipUnless('recovery' in settings.DATABASES, 'Requires isolated recovery DB')
    def test_full_plus_incremental_rebuilds_changed_deleted_rows_and_media(self):
        from .incremental_archive import create_delta_archive
        from .chain_recovery import recover_chain
        from .snapshot import open_media
        from .archive import restore_fixture
        from django.db import connections
        first = backup_tenant(self.a.pk)
        self.assertEqual(first.status, 'success', first.error_code)
        full = self.archive(first)
        base = self.root / 'base-stage'
        base.mkdir(mode=0o700)
        verify(full, self.a.pk, output=base)
        previous_fixture = json.loads((base / 'fixture.json').read_bytes())
        previous_media = {'a.txt': __import__('hashlib').sha256(b'A PRIVATE MEDIA').hexdigest()}
        self.ticket.subject = 'UPDATED PRIVATE TICKET'
        self.ticket.save(update_fields=['subject'])
        SupportTicketAttachment.objects.filter(ticket=self.ticket).delete()
        (self.media / 'new.txt').write_bytes(b'NEW PRIVATE MEDIA')
        SupportTicketAttachment.objects.create(ticket=self.ticket, file='new.txt', uploaded_by=self.user)
        current_bytes, files = collect(self.a.pk)
        current_fixture = json.loads(current_bytes)
        current_media = {}
        for name in files:
            with open_media(name) as source:
                current_media[name] = __import__('hashlib').sha256(source.read()).hexdigest()
        delta = self.root / 'incremental.cvb'
        create_delta_archive(delta, self.a.pk, previous_fixture, current_fixture, previous_media, current_media, open_media)
        destination = self.root / 'chain-output'
        reconstructed = recover_chain(full, [delta], self.a.pk, destination)
        self.assertEqual(reconstructed, current_fixture)
        self.assertEqual((destination / 'media/new.txt').read_bytes(), b'NEW PRIVATE MEDIA')
        self.assertFalse((destination / 'media/a.txt').exists())
        restore_fixture(destination / 'fixture.json', self.a.pk, 'recovery')
        recovered_ticket = SupportTicket.objects.using('recovery').get(pk=self.ticket.pk)
        self.assertEqual(recovered_ticket.subject, 'UPDATED PRIVATE TICKET')
        self.assertEqual(SupportTicketAttachment.objects.using('recovery').count(), 1)
        self.assertEqual(SupportTicketAttachment.objects.using('recovery').get().file.name, 'new.txt')

    def test_chain_service_publishes_only_verified_increment(self):
        from .chain_service import create_verified_increment
        first = backup_tenant(self.a.pk)
        self.assertEqual(first.status, 'success', first.error_code)
        self.ticket.subject = 'Changed after full'
        self.ticket.save(update_fields=['subject'])
        (self.media / 'next.txt').write_bytes(b'NEXT MEDIA')
        SupportTicketAttachment.objects.create(ticket=self.ticket, file='next.txt', uploaded_by=self.user)
        name = create_verified_increment(self.a.pk, first.archive_name)
        self.assertTrue(name.endswith('.delta.cvb'))
        archive = self.disk / f'tenant-{self.a.pk}' / name
        self.assertTrue(archive.is_file())
        self.assertNotIn(b'NEXT MEDIA', archive.read_bytes())
        from .chain_recovery import recover_chain
        result = self.root / 'chain-service-recovery'
        fixture = recover_chain(self.archive(first), [archive], self.a.pk, result)
        self.assertTrue(any(row['model'] == 'cw_auth.supportticket' and row['fields'].get('subject') == 'Changed after full' for row in fixture))
        self.assertEqual((result / 'media/next.txt').read_bytes(), b'NEXT MEDIA')

    def test_scheduled_chain_tracks_incremental_parent_and_base(self):
        from .scheduled_chain import execute_tenant, plan_tenant
        from .chain_history import latest_chain
        from datetime import timedelta
        first = backup_tenant(self.a.pk)
        self.assertEqual(first.status, 'success', first.error_code)
        self.ticket.subject = 'scheduled next day'
        self.ticket.save(update_fields=['subject'])
        next_day = (first.finished_at or first.started_at) + timedelta(days=1)
        plan, base, _ = plan_tenant(self.a.pk, next_day)
        self.assertEqual(plan.action, 'incremental')
        self.assertTrue(self.archive(first).is_file(), (first.archive_name, str(self.archive(first))))
        self.assertEqual(base.archive_name, first.archive_name)
        second = execute_tenant(self.a.pk, next_day)
        self.assertEqual(second.backup_kind, 'incremental')
        self.assertEqual(second.parent_run_id, first.pk)
        self.assertEqual(second.base_run_id, first.pk)
        selected_base, deltas = latest_chain(self.a.pk)
        self.assertEqual(selected_base.pk, first.pk)
        self.assertEqual([item.pk for item in deltas], [second.pk])
        self.assertTrue((self.disk / f'tenant-{self.a.pk}' / second.archive_name).exists())

    def test_scheduled_full_preserves_older_chain_archives(self):
        from .scheduled_chain import execute_tenant
        from datetime import timedelta
        from unittest.mock import patch
        first = backup_tenant(self.a.pk)
        self.assertEqual(first.status, 'success')
        old_path = self.archive(first)
        with patch('apps.cloud_backup.service.settings.CLOUD_BACKUP_KEEP_VERSIONS', 2), patch('apps.cloud_backup.service.timezone.now', return_value=first.finished_at + timedelta(days=45)):
            with patch('apps.cloud_backup.service.eligible', return_value=True):
                for _ in range(3):
                    self.assertEqual(backup_tenant(self.a.pk, preserve_chains=True).status, 'success')
        self.assertTrue(old_path.exists(), 'A full chain base must not be pruned by legacy retention')
    def test_customer_foreign_tenant_relation_still_blocks_backup(self):
        customer = CustomerProfile.objects.create(tenant=self.b, phone='09123330000')
        from django.db import models
        seed_legacy_vehicles([
            VehicleEntry(tenant=self.a, customer=customer, plate_number='mismatched')
        ])
        run = backup_tenant(self.a.pk)
        self.assertEqual(run.error_code, 'foreign_tenant_relation')
        self.assertFalse(list(self.disk.rglob('*.cvb')))

    def test_hq_support_reference_is_redacted_even_when_assigned_to_other_tenant(self):
        hq = User.objects.create_user(username='HQ-PRIVATE-IDENTITY', tenant=self.b,
                                      platform_role='hq_support', phone='09129990000')
        self.ticket.assigned_to = hq
        self.ticket.save()
        SupportTicketMessage.objects.create(ticket=self.ticket, sender=hq, body='Tenant-specific answer')
        fixture, _ = collect(self.a.pk)
        self.assertNotIn(hq.username.encode(), fixture)
        self.assertNotIn(hq.phone.encode(), fixture)
        rows = json.loads(fixture)
        self.assertIsNone(next(r for r in rows if r['model'] == 'cw_auth.supportticket')['fields']['assigned_to'])
        self.assertIsNone(next(r for r in rows if r['model'] == 'cw_auth.supportticketmessage')['fields']['sender'])
        fixture_b, _ = collect(self.b.pk)
        self.assertNotIn(hq.username.encode(), fixture_b)

    def test_limit_diagnosis_reports_only_aggregate_metadata_without_writing(self):
        output = io.StringIO()
        with self.settings(CLOUD_BACKUP_MAX_ROWS=1):
            call_command('diagnose_cloud_backup', tenant=self.a.pk, stdout=output)
        result = json.loads(output.getvalue())
        self.assertEqual(result['code'], 'snapshot_limit_exceeded')
        self.assertEqual(result['diagnostics']['metric'], 'rows')
        self.assertGreater(result['diagnostics']['observed'], result['diagnostics']['limit'])
        for private in ('A private', 'A PRIVATE MEDIA', self.user.username):
            self.assertNotIn(private, output.getvalue())
        self.assertFalse(BackupRun.objects.exists())
        self.assertFalse(list(self.disk.iterdir()))

    def test_field_limit_counts_utf8_bytes_without_exposing_value(self):
        self.ticket.subject = 'آ' * 100
        self.ticket.save()
        with self.settings(CLOUD_BACKUP_MAX_FIELD_BYTES=150):
            with self.assertRaises(SnapshotError) as error:
                collect(self.a.pk)
        self.assertEqual(error.exception.diagnostics['observed'], 200)
        self.assertEqual(error.exception.diagnostics['limit'], 150)
        self.assertNotIn('آ', str(error.exception.diagnostics))

    @skipUnless('recovery' in settings.DATABASES, 'Requires isolated recovery database')
    def test_same_phone_two_tenants_backup_and_restore_independently(self):
        CarWashFeaturePurchase.objects.create(tenant=self.b, feature_key='cloud_storage', is_active=True)
        scores = {self.a.pk: Decimal('1.5'), self.b.pk: Decimal('3.0')}
        for tenant in (self.a, self.b):
            customer = CustomerProfile.objects.create(tenant=tenant, phone='09121112222', yearly_score=scores[tenant.pk])
            VehicleEntry.objects.create(tenant=tenant, customer=customer, plate_number=f'own-{tenant.pk}')
        for tenant in (self.a, self.b):
            run = backup_tenant(tenant.pk)
            self.assertEqual(run.status, 'success', run.error_code)
            archive = self.disk / f'tenant-{tenant.pk}' / run.archive_name
            output = self.root / f'restore-{tenant.pk}'
            call_command('recover_cloud_backup', str(archive), tenant=tenant.pk, output=str(output),
                         database='recovery', confirm_isolated_restore=True)
            self.assertEqual(list(CarWash.objects.using('recovery').values_list('pk', flat=True)), [tenant.pk])
            restored = CustomerProfile.objects.using('recovery').get()
            self.assertEqual(restored.tenant_id, tenant.pk)
            self.assertEqual(restored.yearly_score, scores[tenant.pk])
            self.assertEqual(VehicleEntry.objects.using('recovery').get().customer_id, restored.pk)
            own_file, foreign_file = ('a.txt', 'b.txt') if tenant.pk == self.a.pk else ('b.txt', 'a.txt')
            self.assertTrue((output / 'media' / own_file).exists())
            self.assertFalse((output / 'media' / foreign_file).exists())
            call_command('flush', database='recovery', interactive=False, verbosity=0)

    @skipUnless('recovery' in settings.DATABASES, 'Requires isolated recovery database')
    def test_customer_repair_then_backup_and_isolated_restore(self):
        from cryptography.fernet import Fernet
        from django.db import models
        from apps.vehicles.customer_tenant_repair import make_plan, digest
        from apps.vehicles.tests.guard_support import apply_plan
        customer = CustomerProfile.objects.create(tenant=self.b, phone='09123330000', full_name='FOREIGN CUSTOMER SECRET')
        seed_legacy_vehicles([
            VehicleEntry(tenant=self.a, customer=customer, plate_number='own', driver_phone='09121112222')
        ])
        with patch.dict(os.environ, CUSTOMER_REPAIR_KEY=Fernet.generate_key().decode()):
            plan = make_plan(self.a.pk)
            apply_plan(plan, digest(plan))
        run = backup_tenant(self.a.pk)
        self.assertEqual(run.status, 'success', run.error_code)
        output = self.root / 'repaired-recovery'
        call_command('recover_cloud_backup', str(self.archive(run)), tenant=self.a.pk,
                     output=str(output), database='recovery', confirm_isolated_restore=True, stdout=io.StringIO())
        restored = VehicleEntry.objects.using('recovery').get()
        self.assertEqual(restored.customer.tenant_id, self.a.pk)
        self.assertFalse(CustomerProfile.objects.using('recovery').filter(tenant=self.b).exists())
        self.assertNotIn(b'FOREIGN CUSTOMER SECRET', (output / 'fixture.json').read_bytes())
        self.assertNotIn(b'customertenantrepairrun', (output / 'fixture.json').read_bytes())
