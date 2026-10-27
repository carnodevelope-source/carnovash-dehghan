from unittest.mock import patch
from django.test import TransactionTestCase
from .tests import CloudBackupTests
from .models import BackupRun
from .scheduled_chain import execute_tenant
from .automatic_retention import maintain_run
from .snapshot import SnapshotError

class AutomaticRetentionTests(TransactionTestCase):
    databases=CloudBackupTests.databases
    setUp=CloudBackupTests.setUp
    archive=CloudBackupTests.archive

    def test_successful_backup_records_verified_empty_retention_plan(self):
        run=execute_tenant(self.a.pk)
        lines=[]
        self.assertTrue(maintain_run(run,output=lines.append))
        run.refresh_from_db()
        self.assertEqual(run.retention_status,'success')
        self.assertIsNotNone(run.retention_checked_at)
        self.assertTrue(any('retention_plan' in line for line in lines))
        self.assertTrue(self.archive(run).exists())

    def test_unmanaged_archive_preserves_every_file_and_records_failure(self):
        run=execute_tenant(self.a.pk)
        unknown=self.archive(run).parent/'unmanaged.cvb'
        unknown.write_bytes(b'unknown')
        self.assertFalse(maintain_run(run))
        run.refresh_from_db()
        self.assertEqual((run.status,run.retention_status,run.retention_error_code),('success','failed','unmanaged_archive'))
        self.assertTrue(unknown.exists())
        self.assertTrue(self.archive(run).exists())

    def test_changed_plan_never_authorizes_deletion(self):
        run=execute_tenant(self.a.pk)
        with patch('apps.cloud_backup.automatic_retention.retain_tenant',side_effect=[{'token':'before'},SnapshotError('retention_plan_changed')]):
            self.assertFalse(maintain_run(run))
        run.refresh_from_db()
        self.assertEqual(run.retention_error_code,'retention_plan_changed')
        self.assertTrue(self.archive(run).exists())
