from contextlib import nullcontext
from unittest.mock import patch
from django.test import TransactionTestCase
from .tests import CloudBackupTests
from .models import BackupRun
from .storage_audit import audit_tenant
from . import service

class StorageAuditTests(TransactionTestCase):
    databases=CloudBackupTests.databases
    setUp=CloudBackupTests.setUp
    archive=CloudBackupTests.archive

    def audit(self):
        with patch.object(service,'pinned_root',lambda **kwargs:nullcontext(self.disk)):
            return audit_tenant(self.a.pk)

    def test_readonly_audit_checks_registered_archive_without_mutation(self):
        run=service.backup_tenant(self.a.pk)
        before=self.archive(run).read_bytes()
        count=BackupRun.objects.count()
        result=self.audit()
        self.assertEqual(result['files'][0]['integrity'],'verified')
        self.assertTrue(result['files'][0]['registered_success'])
        self.assertFalse(result['deletion_authorized'])
        self.assertEqual(self.archive(run).read_bytes(),before)
        self.assertEqual(BackupRun.objects.count(),count)

    def test_corrupt_unregistered_archive_is_preserved(self):
        run=service.backup_tenant(self.a.pk)
        BackupRun.objects.filter(pk=run.pk).delete()
        self.archive(run).write_bytes(b'corrupt')
        result=self.audit()
        self.assertFalse(result['files'][0]['registered_success'])
        self.assertEqual(result['files'][0]['integrity'],'failed')
        self.assertEqual(result['deletion_candidates'],[])
        self.assertEqual(self.archive(run).read_bytes(),b'corrupt')
