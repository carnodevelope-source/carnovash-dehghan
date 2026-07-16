from datetime import date, datetime, time
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.auth.models import CarWash
from apps.auth.nightly_sms import dispatch_due_nightly_manager_summaries
from apps.notifications.models import NotificationLog
from apps.payments.models import CashflowTransaction, Payment, Wallet
from apps.vehicles.models import VehicleEntry


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
        wallet_in = CashflowTransaction.objects.create(
            tenant=self.tenant,
            wallet=self.wallet,
            direction=CashflowTransaction.Direction.IN,
            amount=Decimal('300000'),
            created_by=self.manager,
        )
        wallet_out = CashflowTransaction.objects.create(
            tenant=self.tenant,
            wallet=self.wallet,
            direction=CashflowTransaction.Direction.OUT,
            amount=Decimal('120000'),
            created_by=self.manager,
        )
        CashflowTransaction.objects.filter(id=wallet_in.id).update(transacted_at=self._at(day, 9))
        CashflowTransaction.objects.filter(id=wallet_out.id).update(transacted_at=self._at(day, 15))

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
        self.assertEqual(log.payload['wallet_in_total'], 300000.0)
        self.assertEqual(log.payload['wallet_out_total'], 120000.0)
        self.assertIn('درآمد: ۸۵۰،۰۰۰ تومان', log.payload['text'])
        self.assertIn('ورود: ۱ | خروج: ۱', log.payload['text'])

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
