from datetime import date, datetime, time, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.auth.models import CarWash
from apps.auth.nightly_sms import _resolve_target_day, dispatch_due_nightly_manager_summaries
from apps.notifications.models import NotificationLog
from apps.payments.models import Payment, Wallet
from apps.vehicles.models import VehicleEntry, VehicleStatusLog


@override_settings(
    IRANPAYAMAK_API_KEY='test-api-key',
    IRANPAYAMAK_LINE_NUMBER='30001234',
    IRANPAYAMAK_BASE_URL='https://api.iranpayamak.com',
)
class NightlyManagerSmsTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.tenant = CarWash.objects.create(name='کارواش تست', slug='nightly-summary')
        self.manager = user_model.objects.create_user(
            username='nightly-manager',
            password='pass12345',
            phone='09120000001',
            role='manager',
            tenant=self.tenant,
        )
        user_model.objects.create_user(
            username='nightly-manager-2',
            password='pass12345',
            phone='09120000002',
            role='manager',
            tenant=self.tenant,
        )
        self.wallet = Wallet.objects.create(
            tenant=self.tenant,
            name='کیف پول اصلی',
            wallet_type=Wallet.WalletType.BANK,
            balance=1000000,
            is_active=True,
        )

    def _at(self, day, hour):
        return timezone.make_aware(datetime.combine(day, time(hour=hour)))

    @patch('apps.auth.sms.send_provider_sms')
    def test_nightly_summary_uses_real_day_data_and_sends_once_per_tenant_day(self, mock_send_provider_sms):
        mock_send_provider_sms.return_value = {
            'ok': True,
            'message': 'sent',
            'provider_status': 200,
            'provider_data': {'status': 'success', 'data': {'id': 'nightly-1'}},
            'provider_id': 'nightly-1',
            'raw_body': '{"status":"success","data":{"id":"nightly-1"}}',
            'payload': {'line_number': '30001234', 'recipients': ['09120000001']},
        }
        day = date(2026, 7, 16)
        vehicle = VehicleEntry.objects.create(
            tenant=self.tenant,
            plate_number='22 ب 377 54',
            plate_left='54',
            plate_letter='ب',
            plate_mid='377',
            plate_right='22',
            car_model='سمند',
            car_color='سفید',
            driver_name='مشتری تست',
            driver_phone='09121111111',
            status=VehicleEntry.Status.RELEASED,
            entered_by=self.manager,
        )
        VehicleEntry.objects.filter(id=vehicle.id).update(
            check_in_at=self._at(day, 10),
            released_at=self._at(day, 12),
        )
        Payment.objects.create(
            tenant=self.tenant,
            vehicle_entry=vehicle,
            method=Payment.Method.CASH,
            status=Payment.Status.SUCCESS,
            amount=Decimal('850000'),
            paid_at=self._at(day, 12),
            created_by=self.manager,
        )
        for status in [
            VehicleEntry.Status.ENTERED,
            VehicleEntry.Status.ASSIGNED,
            VehicleEntry.Status.IN_PROGRESS,
            VehicleEntry.Status.READY_TO_SETTLE,
            VehicleEntry.Status.CANCELLED,
            VehicleEntry.Status.CANCELLED,
        ]:
            entry = VehicleEntry.objects.create(
                tenant=self.tenant, plate_number='11 ب 111 11',
                status=status, entered_by=self.manager,
            )
            # Cars still inside include admissions from earlier days.
            VehicleEntry.objects.filter(pk=entry.pk).update(check_in_at=self._at(day - timedelta(days=1), 10))
            history = VehicleStatusLog.objects.create(tenant=self.tenant, vehicle=entry, to_status=status)
            VehicleStatusLog.objects.filter(pk=history.pk).update(changed_at=self._at(day - timedelta(days=1), 10))
            if status == VehicleEntry.Status.CANCELLED:
                for _ in range(2):
                    log = VehicleStatusLog.objects.create(
                        tenant=self.tenant, vehicle=entry,
                        to_status=VehicleEntry.Status.CANCELLED,
                    )
                    VehicleStatusLog.objects.filter(pk=log.pk).update(changed_at=self._at(day, 15))
        old_cancel = VehicleEntry.objects.create(
            tenant=self.tenant, plate_number='11 ب 112 11', status=VehicleEntry.Status.CANCELLED,
        )
        VehicleEntry.objects.filter(pk=old_cancel.pk).update(check_in_at=self._at(day - timedelta(days=1), 10))
        old_log = VehicleStatusLog.objects.create(
            tenant=self.tenant, vehicle=old_cancel, to_status=VehicleEntry.Status.CANCELLED,
        )
        VehicleStatusLog.objects.filter(pk=old_log.pk).update(changed_at=self._at(day - timedelta(days=1), 15))

        first_count = dispatch_due_nightly_manager_summaries(target_day=day, force=True)
        second_count = dispatch_due_nightly_manager_summaries(target_day=day, force=True)

        self.assertEqual(first_count, 1)
        self.assertEqual(second_count, 0)
        self.assertEqual(mock_send_provider_sms.call_count, 1)
        log = NotificationLog.objects.get(
            tenant=self.tenant,
            template_code=f'nightly_manager_summary:{self.tenant.id}:{day.isoformat()}',
            status=NotificationLog.Status.SENT,
        )
        self.assertEqual(log.recipient, '09120000001')
        self.assertEqual(log.payload['paid_total'], 850000.0)
        self.assertEqual(log.payload['vehicle_in_count'], 1)
        self.assertEqual(log.payload['vehicle_out_count'], 1)
        self.assertEqual(log.payload['vehicle_pending_count'], 0)
        self.assertEqual(log.payload['vehicle_cancelled_count'], 2)
        self.assertEqual(log.payload['vehicle_remaining_count'], 4)
        self.assertIn('لغو شده‌ها: ۲', log.payload['text'])
        self.assertNotIn('واریز صندوق', log.payload['text'])
        self.assertNotIn('برداشت صندوق', log.payload['text'])
        self.assertIn('گزارش شبانه کارواش تست', log.payload['text'])
        self.assertIn('درآمد وصول‌شده: ۸۵۰،۰۰۰ تومان', log.payload['text'])
        self.assertIn('خودروهای پذیرش‌شده: ۱', log.payload['text'])
        self.assertIn('خودروهای ترخیص‌شده: ۱', log.payload['text'])

    @patch('apps.auth.sms.send_provider_sms')
    def test_nightly_summary_respects_existing_legacy_log_for_same_day(self, mock_send_provider_sms):
        day = date(2026, 7, 16)
        NotificationLog.objects.create(
            tenant=self.tenant,
            channel=NotificationLog.Channel.SMS,
            recipient=self.manager.phone,
            template_code=f'nightly_manager_summary:{day.isoformat()}',
            payload={'report_date': day.isoformat()},
            status=NotificationLog.Status.SENT,
            sent_at=timezone.now(),
            created_by=self.manager,
        )

        sent_count = dispatch_due_nightly_manager_summaries(target_day=day, force=True)

        self.assertEqual(sent_count, 0)
        mock_send_provider_sms.assert_not_called()

    def test_nightly_summary_becomes_due_at_2359(self):
        day = date(2026, 7, 16)

        self.assertIsNone(_resolve_target_day(self._at(day, 23).replace(minute=58)))
        self.assertEqual(_resolve_target_day(self._at(day, 23).replace(minute=59)), day)
        self.assertEqual(_resolve_target_day(self._at(day + timedelta(days=1), 1)), day)

    def _entry(self, day, status, *, tenant=None, released_at=None, history=True):
        tenant = tenant or self.tenant
        entry = VehicleEntry.objects.create(tenant=tenant, status=status)
        VehicleEntry.objects.filter(pk=entry.pk).update(check_in_at=self._at(day, 10), released_at=released_at)
        if history:
            self._transition(entry, status, self._at(day, 10))
        return entry

    def _transition(self, entry, status, at, source=''):
        log = VehicleStatusLog.objects.create(
            tenant=entry.tenant, vehicle=entry, from_status=source, to_status=status,
        )
        VehicleStatusLog.objects.filter(pk=log.pk).update(changed_at=at)
        VehicleEntry.objects.filter(pk=entry.pk).update(status=status)

    def _report(self, day, now=None):
        with patch('apps.auth.nightly_sms.send_logged_sms', return_value={'ok': True}) as send:
            dispatch_due_nightly_manager_summaries(target_day=day, now=now)
        return send.call_args_list

    def test_all_83_admissions_released_same_day(self):
        day = date(2026, 10, 25)
        for _ in range(83):
            self._entry(day, VehicleEntry.Status.RELEASED, released_at=self._at(day, 15), history=False)
        call = self._report(day)[0].kwargs
        self.assertEqual(call['payload']['vehicle_in_count'], 83)
        self.assertEqual(call['payload']['vehicle_out_count'], 83)
        self.assertEqual(call['payload']['vehicle_pending_count'], 0)
        self.assertEqual(call['payload']['vehicle_remaining_count'], 0)
        self.assertIn('\u0622\u0645\u0627\u062f\u0647 \u062a\u0631\u062e\u06cc\u0635: \u06f0', call['text'])

    def test_delayed_report_keeps_ready_and_old_active_inventory(self):
        day = date(2026, 7, 16)
        self._entry(day - timedelta(days=30), VehicleEntry.Status.IN_PROGRESS)
        ready = self._entry(day, VehicleEntry.Status.READY_TO_SETTLE)
        self._transition(ready, VehicleEntry.Status.RELEASED, self._at(day + timedelta(days=1), 1), VehicleEntry.Status.READY_TO_SETTLE)
        VehicleEntry.objects.filter(pk=ready.pk).update(released_at=self._at(day + timedelta(days=1), 1))
        early = self._report(day, self._at(day + timedelta(days=1), 2))[0].kwargs['payload']
        late = self._report(day, self._at(day + timedelta(days=10), 2))[0].kwargs['payload']
        self.assertEqual(early, late)
        self.assertEqual(late['vehicle_pending_count'], 1)
        self.assertEqual(late['vehicle_remaining_count'], 2)
        self.assertEqual(late['vehicle_out_count'], 0)

    def test_cancellation_and_release_events_survive_later_restoration(self):
        day = date(2026, 7, 16)
        cancelled = self._entry(day, VehicleEntry.Status.CANCELLED)
        released = self._entry(day, VehicleEntry.Status.RELEASED)
        for entry in (cancelled, released):
            self._transition(entry, VehicleEntry.Status.ENTERED, self._at(day + timedelta(days=1), 10))
        payload = self._report(day)[0].kwargs['payload']
        self.assertEqual(payload['vehicle_cancelled_count'], 1)
        self.assertEqual(payload['vehicle_out_count'], 1)
        self.assertEqual(payload['vehicle_remaining_count'], 0)

    def test_missing_history_uses_recorded_status_for_daily_ready_count(self):
        day = date(2026, 7, 16)
        self._entry(day, VehicleEntry.Status.READY_TO_SETTLE, history=False)
        call = self._report(day)[0].kwargs
        self.assertEqual(call['payload']['vehicle_pending_count'], 1)
        self.assertIsNone(call['payload']['vehicle_remaining_count'])
        self.assertEqual(call['payload']['history_unknown_count'], 1)
        self.assertNotIn('نامشخص', call['text'])
        self.assertNotIn('کل خودروهای باقی', call['text'])
        self.assertNotIn('تاریخچه ناکافی', call['text'])

    def test_daily_ready_count_excludes_old_released_and_unfinished_entries(self):
        day = date(2026, 7, 16)
        self._entry(day - timedelta(days=1), VehicleEntry.Status.READY_TO_SETTLE)
        self._entry(day, VehicleEntry.Status.IN_PROGRESS, history=False)
        self._entry(day, VehicleEntry.Status.RELEASED, released_at=self._at(day, 15), history=False)
        self.assertEqual(self._report(day)[0].kwargs['payload']['vehicle_pending_count'], 0)
        for _ in range(3):
            self._entry(day, VehicleEntry.Status.READY_TO_SETTLE, history=False)
        call = self._report(day)[0].kwargs
        self.assertEqual(call['payload']['vehicle_pending_count'], 3)
        self.assertIn('\u0622\u0645\u0627\u062f\u0647 \u062a\u0631\u062e\u06cc\u0635: \u06f3', call['text'])

    def test_next_transition_source_reconstructs_previous_day(self):
        day = date(2026, 7, 16)
        entry = self._entry(day, VehicleEntry.Status.RELEASED, history=False)
        self._transition(entry, VehicleEntry.Status.RELEASED, self._at(day + timedelta(days=1), 1), VehicleEntry.Status.READY_TO_SETTLE)
        payload = self._report(day)[0].kwargs['payload']
        self.assertEqual(payload['vehicle_pending_count'], 1)
        self.assertEqual(payload['vehicle_remaining_count'], 1)

    @override_settings(TIME_ZONE='UTC')
    def test_tehran_boundaries_and_tenant_isolation(self):
        from apps.auth.nightly_sms import REPORT_TZ, _day_bounds
        day = date(2026, 7, 16)
        start, end = _day_bounds(day)
        other = CarWash.objects.create(name='Other', slug='other-nightly')
        get_user_model().objects.create_user(username='other-manager', phone='09120000003', role='manager', tenant=other)
        entry = self._entry(day, VehicleEntry.Status.READY_TO_SETTLE)
        VehicleEntry.objects.filter(pk=entry.pk).update(check_in_at=start)
        self._entry(day, VehicleEntry.Status.IN_PROGRESS, tenant=other)
        future = self._entry(day, VehicleEntry.Status.READY_TO_SETTLE)
        VehicleEntry.objects.filter(pk=future.pk).update(check_in_at=end)
        self._transition(entry, VehicleEntry.Status.RELEASED, end, VehicleEntry.Status.READY_TO_SETTLE)
        VehicleEntry.objects.filter(pk=entry.pk).update(released_at=end)
        calls = self._report(day)
        payloads = {c.kwargs['tenant'].pk: c.kwargs['payload'] for c in calls}
        self.assertEqual(payloads[self.tenant.pk]['vehicle_in_count'], 1)
        self.assertEqual(payloads[self.tenant.pk]['vehicle_out_count'], 0)
        self.assertEqual(payloads[self.tenant.pk]['vehicle_pending_count'], 1)
        self.assertEqual(payloads[other.pk]['vehicle_pending_count'], 0)
        self.assertEqual(payloads[other.pk]['vehicle_remaining_count'], 1)
        self.assertEqual(start.utcoffset(), timedelta(hours=3, minutes=30))
        self.assertEqual(_resolve_target_day(end.astimezone(REPORT_TZ)), day)

    def test_does_not_send_incomplete_day_even_when_forced(self):
        day = date(2026, 7, 16)
        with patch('apps.auth.nightly_sms.send_logged_sms') as send:
            self.assertEqual(dispatch_due_nightly_manager_summaries(target_day=day, now=self._at(day, 23).replace(minute=59), force=True), 0)
        send.assert_not_called()

    def test_daily_payment_and_cancellation_bounds(self):
        from apps.auth.nightly_sms import _day_bounds
        day = date(2026, 7, 16)
        start, end = _day_bounds(day)
        entry = self._entry(day, VehicleEntry.Status.ENTERED)
        self._transition(entry, VehicleEntry.Status.CANCELLED, end, VehicleEntry.Status.ENTERED)
        for at, amount in ((start - timedelta(microseconds=1), 100), (start, 200), (end - timedelta(microseconds=1), 300), (end, 400)):
            Payment.objects.create(tenant=self.tenant, vehicle_entry=entry, method=Payment.Method.CASH,
                                   status=Payment.Status.SUCCESS, amount=amount, paid_at=at)
        fallback = Payment.objects.create(tenant=self.tenant, vehicle_entry=entry, method=Payment.Method.CASH,
                                         status=Payment.Status.SUCCESS, amount=50)
        Payment.objects.filter(pk=fallback.pk).update(created_at=start)
        Payment.objects.create(tenant=self.tenant, vehicle_entry=entry, method=Payment.Method.CASH,
                               status=Payment.Status.FAILED, amount=900, paid_at=start)
        payload = self._report(day)[0].kwargs['payload']
        self.assertEqual(payload['paid_total'], 550)
        self.assertEqual(payload['vehicle_cancelled_count'], 0)
        self.assertEqual(payload['vehicle_remaining_count'], 1)
