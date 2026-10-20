from unittest.mock import patch

from django.test import SimpleTestCase

from apps.auth.scheduler import _run_background_jobs_once


class SchedulerRealtimePruneTests(SimpleTestCase):
    @patch('apps.reports.monthly_wages.accrue_monthly_wages_for_day')
    @patch('django.core.management.call_command')
    @patch('apps.subscriptions.services.run_expiry_and_reminder_jobs')
    @patch('apps.auth.support_tickets.close_stale_support_tickets')
    @patch('apps.auth.nightly_sms.dispatch_due_nightly_manager_summaries')
    def test_background_cycle_prunes_technical_realtime_rows(
        self, _nightly, _tickets, _expiry, call_command, accrue_wages,
    ):
        _run_background_jobs_once()
        call_command.assert_called_once_with('prune_realtime_records')
        from django.utils import timezone
        accrue_wages.assert_called_once_with(timezone.localdate())
