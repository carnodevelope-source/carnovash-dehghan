"""Real ORM/encryption/recovery regression tests on disposable databases."""
import os
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from django.test import TransactionTestCase
from django.utils import timezone
from .tests import CloudBackupTests
from .models import BackupRun
from . import service
from .snapshot import SnapshotError
from .scheduled_chain import execute_tenant, plan_tenant
from .chain_history import latest_chain
from .staging import private_staging, cleanup_staging
from .management.commands.run_cloud_backup_chains import should_attempt

REAL_LOCK = service.tenant_lock


class ChainLifecycleTests(TransactionTestCase):
    databases = CloudBackupTests.databases
    setUp = CloudBackupTests.setUp
    archive = CloudBackupTests.archive

    def first(self):
        run = execute_tenant(self.a.pk)
        self.assertEqual(run.status, 'success', run.error_code)
        return run

    def test_full_history_is_saved_while_locked(self):
        held = []
        original = BackupRun.save
        @contextmanager
        def lock(_):
            held.append(True)
            try:
                yield
            finally:
                held.pop()
        def save(obj, *args, **kwargs):
            if obj.status == 'success':
                self.assertTrue(held)
            return original(obj, *args, **kwargs)
        with patch.object(service, 'tenant_lock', lock), patch.object(BackupRun, 'save', save):
            self.first()

    def test_increment_history_is_saved_while_locked(self):
        first = self.first()
        held = []
        original = BackupRun.save
        @contextmanager
        def lock(_):
            held.append(True)
            try:
                yield
            finally:
                held.pop()
        def save(obj, *args, **kwargs):
            if obj.status == 'success':
                self.assertTrue(held)
            return original(obj, *args, **kwargs)
        with patch.object(service, 'tenant_lock', lock), patch.object(BackupRun, 'save', save):
            second = execute_tenant(self.a.pk, first.started_at + timedelta(days=1))
        self.assertEqual(second.status, 'success', second.error_code)
        self.assertEqual(second.backup_kind, 'incremental')

    def test_same_day_is_durable_across_restart(self):
        first = self.first()
        self.assertIsNone(execute_tenant(self.a.pk, first.started_at))
        self.assertEqual(BackupRun.objects.filter(status='success').count(), 1)
        self.assertFalse(should_attempt(self.a.pk, timezone.now()))

    def test_real_flock_rejects_concurrent_scheduler(self):
        first = self.first()
        directory = self.archive(first).parent
        with patch.object(service, 'tenant_lock', REAL_LOCK):
            with REAL_LOCK(directory):
                self.assertIsNone(execute_tenant(self.a.pk, first.started_at + timedelta(days=1)))
        self.assertEqual(BackupRun.objects.count(), 1)

    def test_missing_base_forces_full(self):
        first = self.first()
        self.archive(first).unlink()  # Only this test's scratch fixture.
        second = execute_tenant(self.a.pk, first.started_at + timedelta(days=1))
        self.assertEqual((second.status, second.backup_kind), ('success', 'full'))

    def test_corrupt_base_forces_full_even_same_day(self):
        first = self.first()
        self.archive(first).write_bytes(b'corrupt')
        second = execute_tenant(self.a.pk, first.started_at)
        self.assertEqual((second.status, second.backup_kind), ('success', 'full'))

    def test_publication_failure_is_tracked_without_success(self):
        first = self.first()
        original = BackupRun.save
        def save(obj, *args, **kwargs):
            if obj.backup_kind == 'incremental' and obj.status == 'success':
                raise RuntimeError('secret SQL password must not persist')
            return original(obj, *args, **kwargs)
        with patch.object(BackupRun, 'save', save):
            second = execute_tenant(self.a.pk, first.started_at + timedelta(days=1))
        self.assertEqual(second.status, 'failed')
        self.assertEqual(second.error_code, 'backup_failed')
        self.assertTrue(second.archive_name)
        self.assertTrue(self.archive(second).is_file())
        self.assertEqual(latest_chain(self.a.pk)[0].pk, first.pk)

    def test_history_write_failure_before_publish_leaves_no_orphan(self):
        first = self.first()
        original = BackupRun.save
        def save(obj, *args, **kwargs):
            if obj.backup_kind == 'incremental' and kwargs.get('update_fields') == ['archive_name']:
                raise RuntimeError('DB failed')
            return original(obj, *args, **kwargs)
        with patch.object(BackupRun, 'save', save):
            second = execute_tenant(self.a.pk, first.started_at + timedelta(days=1))
        self.assertEqual(second.status, 'failed')
        self.assertEqual(len(list(self.archive(first).parent.glob('*.cvb'))), 1)
        self.assertFalse(list(self.archive(first).parent.glob('*.partial')))

    def test_forward_parent_is_rejected(self):
        first = self.first()
        second = execute_tenant(self.a.pk, first.started_at + timedelta(days=1))
        BackupRun.objects.filter(pk=first.pk).update(started_at=second.started_at + timedelta(seconds=1))
        # The latest entry becoming full must not hide a future-dated delta.
        BackupRun.objects.filter(pk=second.pk).update(started_at=first.started_at - timedelta(seconds=1))
        # Explicit invalid parent while delta remains latest.
        BackupRun.objects.filter(pk=first.pk).update(started_at=second.started_at)
        BackupRun.objects.filter(pk=second.pk).update(started_at=second.started_at, parent_run_id=second.pk)
        with self.assertRaises(SnapshotError):
            latest_chain(self.a.pk)

    def test_media_mutation_after_collect_is_rejected(self):
        first = self.first()
        from .chain_service import collect
        def changed(tenant_id):
            result = collect(tenant_id)
            (self.media / 'a.txt').write_bytes(b'changed after snapshot')
            return result
        with patch('apps.cloud_backup.chain_service.collect', changed):
            second = execute_tenant(self.a.pk, first.started_at + timedelta(days=1))
        self.assertEqual((second.status, second.error_code), ('failed', 'source_changed'))

    def test_interrupted_run_is_reconciled_under_lock(self):
        abandoned = BackupRun.objects.create(tenant_id=self.a.pk)
        self.first()
        abandoned.refresh_from_db()
        self.assertEqual((abandoned.status, abandoned.error_code), ('failed', 'worker_interrupted'))

    def test_plaintext_staging_is_ram_backed_and_reaped(self):
        with private_staging(self.a.pk) as stage:
            self.assertTrue(str(stage).startswith('/dev/shm/'))
            self.assertEqual(stage.stat().st_mode & 0o777, 0o700)
            (stage / 'secret').write_bytes(b'temporary')
        self.assertFalse(stage.exists())
        import tempfile
        stale = Path(tempfile.mkdtemp(prefix=f'carvash-verify-{os.geteuid()}-{self.a.pk}-', dir='/dev/shm'))
        (stale / 'secret').write_bytes(b'interrupted')
        cleanup_staging(self.a.pk)
        self.assertFalse(stale.exists())

    def test_mount_failure_is_recorded_and_no_archive_published(self):
        with patch.object(service, 'mount_guard', side_effect=SnapshotError('mount_unavailable')):
            result = execute_tenant(self.a.pk)
        self.assertEqual((result.status, result.error_code), ('failed', 'mount_unavailable'))
        self.assertFalse(list(self.disk.rglob('*.cvb')))

    def test_retry_backoff_survives_restart(self):
        now = timezone.now()
        BackupRun.objects.create(tenant_id=self.a.pk, status='failed', finished_at=now)
        self.assertFalse(should_attempt(self.a.pk, now + timedelta(seconds=10)))
        self.assertTrue(should_attempt(self.a.pk, now + timedelta(hours=7)))

    def test_subscription_disabled_during_increment_fails(self):
        first = self.first()
        with patch('apps.cloud_backup.chain_service.service.eligible', side_effect=[True, True, True, False]):
            second = execute_tenant(self.a.pk, first.started_at + timedelta(days=1))
        self.assertEqual(second.status, 'failed')
        self.assertEqual(second.error_code, 'subscription_inactive')

    def test_three_increments_restore_real_database_and_media(self):
        from apps.auth.models import SupportTicket, SupportTicketAttachment, CarWash
        from .chain_recovery import recover_chain
        from .archive import restore_fixture
        from .snapshot import collect, serialize_row
        import json
        first = self.first()
        attachment = SupportTicketAttachment.objects.get(ticket=self.ticket)
        deleted = SupportTicket.objects.create(tenant=self.a, created_by=self.user, subject='delete me')
        runs = []
        for day in range(1, 4):
            self.ticket.subject = f'edit day {day}'
            self.ticket.save()
            if day == 1:
                (self.media / 'new.txt').write_bytes(b'new file')
                SupportTicketAttachment.objects.create(ticket=self.ticket, uploaded_by=self.user, file='new.txt')
            if day == 2:
                deleted.delete()
                (self.media / 'new.txt').write_bytes(b'edited media')
                attachment.delete()
                (self.media / 'a.txt').unlink()
            if day == 3:
                SupportTicket.objects.create(tenant=self.a, created_by=self.user, subject='new record')
            run = execute_tenant(self.a.pk, first.started_at + timedelta(days=day))
            self.assertEqual((run.status, run.backup_kind), ('success', 'incremental'), run.error_code)
            runs.append(run)
        expected, files = collect(self.a.pk)
        target = self.root / 'multi-db-recovery'
        recovered = recover_chain(self.archive(first), [self.archive(r) for r in runs], self.a.pk, target)
        from .delta import fixture_digest
        self.assertEqual(fixture_digest(recovered), fixture_digest(json.loads(expected)))
        restore_fixture(target / 'fixture.json', self.a.pk, 'recovery')
        from django.apps import apps
        for row in json.loads(expected):
            obj = apps.get_model(row['model']).objects.using('recovery').get(pk=row['pk'])
            actual = json.loads(serialize_row(obj))[0]
            if row['model'] == 'cw_auth.user':
                actual['fields'].update(groups=[], user_permissions=[])
            self.assertEqual(actual, row)
        self.assertFalse(CarWash.objects.using('recovery').filter(pk=self.b.pk).exists())
        self.assertEqual((target / 'media/new.txt').read_bytes(), b'edited media')
        self.assertFalse((target / 'media/a.txt').exists())
        self.assertFalse((target / 'media/b.txt').exists())

    def old_chains(self):
        first = self.first()
        runs = [first]
        for day in [10, 20, 30, 40]:
            run = execute_tenant(self.a.pk, first.started_at + timedelta(days=day))
            self.assertEqual((run.status, run.backup_kind), ('success', 'full'))
            runs.append(run)
        return runs, first.started_at + timedelta(days=40)

    def test_retention_dry_run_and_reviewed_token(self):
        from .retention_service import retain_tenant
        runs, now = self.old_chains()
        preview = retain_tenant(self.a.pk, now=now)
        self.assertEqual([r[0] for r in preview['delete']], [runs[0].pk])
        self.assertTrue(self.archive(runs[0]).exists())
        with self.assertRaisesRegex(SnapshotError, 'retention_plan_changed'):
            retain_tenant(self.a.pk, now=now, execute=True, reviewed_token='wrong')
        result = retain_tenant(self.a.pk, now=now, execute=True, reviewed_token=preview['token'])
        self.assertFalse(result['dry_run'])
        self.assertFalse(self.archive(runs[0]).exists())
        for run in runs[1:]:
            self.assertTrue(self.archive(run).exists())

    def test_corruption_cancels_all_retention(self):
        from .retention_service import retain_tenant
        runs, now = self.old_chains()
        self.archive(runs[-1]).write_bytes(b'corrupt replacement')
        with self.assertRaises(SnapshotError):
            retain_tenant(self.a.pk, now=now)
        self.assertTrue(self.archive(runs[0]).exists())

    def test_unmanaged_archive_blocks_retention(self):
        from .retention_service import retain_tenant
        runs, now = self.old_chains()
        (self.archive(runs[0]).parent / 'unknown.cvb').write_bytes(b'unreviewed')
        with self.assertRaisesRegex(SnapshotError, 'unmanaged_archive'):
            retain_tenant(self.a.pk, now=now)
        self.assertTrue(self.archive(runs[0]).exists())

    def test_interrupted_deletion_reconciles_after_verifying_survivors(self):
        from .retention_service import retain_tenant
        runs, now = self.old_chains()
        preview = retain_tenant(self.a.pk, now=now)
        original = service.sync_directory
        with patch.object(service, 'sync_directory', side_effect=OSError('simulated interruption')):
            with self.assertRaises(OSError):
                retain_tenant(self.a.pk, now=now, execute=True, reviewed_token=preview['token'])
        runs[0].refresh_from_db()
        self.assertEqual(runs[0].status, 'deleting')
        new_preview = retain_tenant(self.a.pk, now=now)
        retain_tenant(self.a.pk, now=now, execute=True, reviewed_token=new_preview['token'])
        runs[0].refresh_from_db()
        self.assertEqual(runs[0].status, 'pruned')
        for run in runs[1:]:
            self.assertTrue(self.archive(run).exists())

    def test_forty_day_cycle_preserves_every_retained_restore_point(self):
        from .retention_service import retain_tenant
        from .chain_recovery import recover_chain
        from .delta import fixture_digest
        from .snapshot import collect
        import json
        first = self.first()
        runs = [first]
        expected = {first.pk: fixture_digest(json.loads(collect(self.a.pk)[0]))}
        for day in range(1, 41):
            self.ticket.subject = f'calendar day {day}'
            self.ticket.save()
            run = execute_tenant(self.a.pk, first.started_at + timedelta(days=day))
            self.assertEqual(run.status, 'success', (day, run.error_code))
            self.assertEqual(run.backup_kind, 'full' if day % 10 == 0 else 'incremental')
            runs.append(run)
            expected[run.pk] = fixture_digest(json.loads(collect(self.a.pk)[0]))
        now = first.started_at + timedelta(days=40)
        preview = retain_tenant(self.a.pk, now=now)
        self.assertEqual(len(preview['delete']), 10)
        retain_tenant(self.a.pk, now=now, execute=True, reviewed_token=preview['token'])
        base, deltas = None, []
        for day, run in enumerate(runs):
            if day < 10:
                self.assertFalse(self.archive(run).exists())
                continue
            if run.backup_kind == 'full':
                base, deltas = run, []
            else:
                deltas.append(self.archive(run))
            recovered = recover_chain(self.archive(base), deltas, self.a.pk, self.root / f'day-{day}')
            self.assertEqual(fixture_digest(recovered), expected[run.pk])

    def test_interrupted_increment_is_reconciled_and_partial_removed(self):
        first = self.first()
        partial = self.archive(first).parent / 'killed.delta.cvb.partial'
        def killed(*args, **kwargs):
            partial.write_bytes(b'incomplete encrypted data')
            raise KeyboardInterrupt()
        day = first.started_at + timedelta(days=1)
        with patch('apps.cloud_backup.scheduled_chain.create_verified_increment', killed):
            with self.assertRaises(KeyboardInterrupt):
                execute_tenant(self.a.pk, day)
        self.assertTrue(BackupRun.objects.filter(status='running').exists())
        result = execute_tenant(self.a.pk, day)
        self.assertEqual(result.status, 'success')
        self.assertFalse(partial.exists())
        self.assertTrue(BackupRun.objects.filter(error_code='worker_interrupted').exists())

    def test_reference_to_deleted_media_invalidates_restored_chain(self):
        from .incremental_archive import create_delta_archive
        from .chain_recovery import recover_chain
        from .snapshot import collect
        import json, hashlib
        first = self.first()
        fixture = json.loads(collect(self.a.pk)[0])
        media = {'a.txt': hashlib.sha256((self.media / 'a.txt').read_bytes()).hexdigest()}
        delta = self.root / 'missing-reference.cvb'
        create_delta_archive(delta, self.a.pk, fixture, fixture, media, {}, None)
        destination = self.root / 'bad-reference'
        with self.assertRaisesRegex(SnapshotError, 'missing_media_member'):
            recover_chain(self.archive(first), [delta], self.a.pk, destination)
        self.assertFalse(destination.exists())

    def test_fixture_row_order_does_not_reject_valid_increment(self):
        from apps.auth.models import SupportTicket
        for index in range(12):
            SupportTicket.objects.create(tenant=self.a, created_by=self.user, subject=f'row {index}')
        first = self.first()
        second = execute_tenant(self.a.pk, first.started_at + timedelta(days=1))
        self.assertEqual((second.status, second.backup_kind), ('success', 'incremental'), second.error_code)
