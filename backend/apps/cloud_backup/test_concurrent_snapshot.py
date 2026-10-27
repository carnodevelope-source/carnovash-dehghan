"""Actual concurrent MySQL commits, immutable media and MVCC recovery."""
import json
import queue
import threading
from datetime import timedelta
from unittest import skipUnless
from unittest.mock import patch
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import connection, connections, transaction
from django.test import TransactionTestCase, SimpleTestCase
from apps.auth.models import SupportTicket, SupportTicketAttachment
from config.media_storage import media_read_lock, ImmutableMediaStorage
from .tests import CloudBackupTests
from . import service
from .chain_service import collect as chain_collect
from .scheduled_chain import execute_tenant
from .archive import verify
from .chain_recovery import recover_chain


class ConcurrentSnapshotTests(TransactionTestCase):
    databases = CloudBackupTests.databases
    setUp = CloudBackupTests.setUp
    archive = CloudBackupTests.archive

    def capture(self, *, incremental=False, delete=False):
        first = service.backup_tenant(self.a.pk) if incremental else None
        original = chain_collect if incremental else service.collect
        thread_errors = queue.Queue()
        committed = threading.Event()
        attachment = SupportTicketAttachment.objects.get(ticket=self.ticket)
        old_subject = self.ticket.subject
        names = []
        def update():
            try:
                with transaction.atomic():
                    if delete:
                        SupportTicketAttachment.objects.filter(pk=attachment.pk).delete()
                        default_storage.delete('a.txt')
                    else:
                        name = default_storage.save('a.txt', ContentFile(b'NEW VERSION'))
                        names.append(name)
                        SupportTicketAttachment.objects.filter(pk=attachment.pk).update(file=name)
                        SupportTicket.objects.filter(pk=self.ticket.pk).update(subject='new committed state')
                        default_storage.delete('a.txt')
            except BaseException as exc:
                thread_errors.put(exc)
            finally:
                connections.close_all()
                committed.set()
        def collect_and_update(tenant_id):
            snapshot = original(tenant_id)
            thread = threading.Thread(target=update)
            thread.start()
            self.assertTrue(committed.wait(10), 'Backup blocked ordinary DB writes')
            thread.join(2)
            if not thread_errors.empty():
                raise thread_errors.get()
            return snapshot
        target = 'apps.cloud_backup.chain_service.collect' if incremental else 'apps.cloud_backup.service.collect'
        with patch(target, collect_and_update):
            run = execute_tenant(self.a.pk, first.started_at + timedelta(days=1)) if incremental else service.backup_tenant(self.a.pk)
        self.assertEqual(run.status, 'success', run.error_code)
        result = self.root / 'concurrent-restore'
        if incremental:
            fixture = recover_chain(self.archive(first), [self.archive(run)], self.a.pk, result)
        else:
            result.mkdir(mode=0o700)
            verify(self.archive(run), self.a.pk, output=result)
            fixture = json.loads((result / 'fixture.json').read_bytes())
        old_ticket = next(row for row in fixture if row['model'] == 'cw_auth.supportticket')
        self.assertEqual(old_ticket['fields']['subject'], old_subject)
        self.assertEqual((result / 'media/a.txt').read_bytes(), b'A PRIVATE MEDIA')
        self.assertFalse((result / 'media/b.txt').exists())
        if not delete:
            self.assertNotEqual(names[0], 'a.txt')
            self.assertEqual((self.media / names[0]).read_bytes(), b'NEW VERSION')
        self.assertTrue((self.media / 'a.txt').exists(), 'In-flight snapshot blob deleted')
        # Once readers finish, an explicit physical delete can proceed.
        default_storage.delete('a.txt')
        self.assertFalse((self.media / 'a.txt').exists())

    @skipUnless(connection.vendor == 'mysql', 'Real simultaneous commit requires MySQL')
    def test_full_snapshot_survives_simultaneous_db_and_media_replacement(self):
        self.capture()

    @skipUnless(connection.vendor == 'mysql', 'Real simultaneous commit requires MySQL')
    def test_increment_survives_simultaneous_db_and_media_replacement(self):
        self.capture(incremental=True)

    @skipUnless(connection.vendor == 'mysql', 'Real simultaneous commit requires MySQL')
    def test_snapshot_survives_simultaneous_record_and_file_deletion(self):
        self.capture(delete=True)

    def test_storage_never_overwrites_a_referenced_name(self):
        name = default_storage.save('a.txt', ContentFile(b'replacement'))
        self.assertNotEqual(name, 'a.txt')
        self.assertEqual((self.media / 'a.txt').read_bytes(), b'A PRIVATE MEDIA')
        self.assertEqual((self.media / name).read_bytes(), b'replacement')

    def test_deletion_is_nonblocking_while_snapshot_reads(self):
        with media_read_lock():
            default_storage.delete('a.txt')
            self.assertTrue((self.media / 'a.txt').exists())
        default_storage.delete('a.txt')
        self.assertFalse((self.media / 'a.txt').exists())

    def test_existing_blob_cannot_be_opened_for_writing(self):
        with self.assertRaisesRegex(ValueError,'immutable_media_write_requires_new_name'):
            default_storage.open('a.txt','wb')
        self.assertEqual((self.media/'a.txt').read_bytes(),b'A PRIVATE MEDIA')
