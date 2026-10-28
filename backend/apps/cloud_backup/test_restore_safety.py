"""Restore must preserve historical dates and have no application side effects."""
import json
from contextlib import ExitStack
from datetime import timedelta
from unittest.mock import patch
from django.test import TransactionTestCase
from django.utils import timezone
from apps.auth.models import SupportTicket
from .tests import CloudBackupTests
from .snapshot import collect, SnapshotError
from .archive import restore_fixture


class RestoreSafetyTests(TransactionTestCase):
    databases = CloudBackupTests.databases
    setUp = CloudBackupTests.setUp

    def test_raw_restore_preserves_dates_without_events_sms_or_cache_changes(self):
        old = timezone.now() - timedelta(days=45)
        SupportTicket.objects.filter(pk=self.ticket.pk).update(created_at=old, updated_at=old)
        payload, _ = collect(self.a.pk)
        path = self.root / 'fixture.json'
        path.write_bytes(payload)
        with ExitStack() as stack:
            mocks=[]
            for app in ['auth','vehicles','subscriptions','inventory','workers','payments','services','products','notifications']:
                mocks.append(stack.enter_context(patch(f'apps.{app}.signals.publish_live_event')))
            mocks.append(stack.enter_context(patch('apps.auth.support_tickets.notify_hq_alert_ticket_sms')))
            mocks.append(stack.enter_context(patch('apps.payments.views.invalidate_license_status_cache')))
            restore_fixture(path, self.a.pk, 'recovery')
            for mock in mocks:
                mock.assert_not_called()
        restored=SupportTicket.objects.using('recovery').get(pk=self.ticket.pk)
        expected=next(row for row in json.loads(payload) if row['model']=='cw_auth.supportticket')
        from django.utils.dateparse import parse_datetime
        self.assertEqual(restored.created_at,parse_datetime(expected['fields']['created_at']))
        self.assertEqual(restored.updated_at,parse_datetime(expected['fields']['updated_at']))
        self.assertTrue(SupportTicket.objects.filter(pk=self.ticket.pk).exists())

    def test_missing_media_is_explicit_and_never_silently_skipped(self):
        (self.media / 'a.txt').unlink()
        with self.assertRaisesMessage(SnapshotError,'missing_media'):
            collect(self.a.pk)
