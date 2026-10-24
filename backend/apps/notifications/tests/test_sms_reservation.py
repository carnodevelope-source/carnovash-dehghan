from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate

from apps.auth.models import CarWash
from apps.notifications.services import sms_cost_for_text
from apps.notifications.views import SmsCampaignSendView
from apps.payments.models import CashflowTransaction, Wallet


class SmsReservationTests(APITestCase):
    def setUp(self):
        self.tenant = CarWash.objects.create(name='Reservation test', slug='reservation-test')
        self.user = get_user_model().objects.create_user(
            username='reservation-user', tenant=self.tenant, role='manager',
        )
        self.cost = sms_cost_for_text('Hello')
        self.wallet = Wallet.objects.create(
            tenant=self.tenant, name='SMS', wallet_type=Wallet.WalletType.SMS,
            balance=self.cost,
        )

    def send(self, text='Hello', recipients=None):
        request = APIRequestFactory().post('/sms/', {
            'template_text': text,
            'recipients': recipients or [{'phone': '09120000000'}],
        }, format='json')
        force_authenticate(request, self.user)
        return SmsCampaignSendView.as_view()(request)

    def result(self, ok):
        return {'ok': ok, 'message': 'test', 'payload': {}, 'raw_body': 'test'}

    def test_credit_is_taken_before_provider_and_nested_send_is_rejected(self):
        def provider(**kwargs):
            self.wallet.refresh_from_db()
            self.assertEqual(self.wallet.balance, 0)
            self.assertEqual(self.send().status_code, 402)
            return self.result(True)

        with patch.object(SmsCampaignSendView, '_send_provider_request', side_effect=provider) as send:
            response = self.send()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(send.call_count, 1)
        self.assertEqual(response.data['debited_amount'], self.cost)

    def test_failed_send_refunds_original_wallet(self):
        with patch.object(SmsCampaignSendView, '_send_provider_request', return_value=self.result(False)):
            response = self.send()
        self.wallet.refresh_from_db()
        self.assertEqual(response.status_code, 502)
        self.assertEqual(self.wallet.balance, self.cost)
        self.assertEqual(response.data['debited_amount'], 0)
        self.assertEqual(CashflowTransaction.objects.filter(reference_type='sms_campaign_refund').count(), 1)

    def test_insufficient_credit_does_not_call_provider(self):
        self.wallet.balance = 0
        self.wallet.save()
        with patch.object(SmsCampaignSendView, '_send_provider_request') as send:
            self.assertEqual(self.send().status_code, 402)
        send.assert_not_called()

    def test_insufficient_total_rolls_back_partial_debit(self):
        recipients = [{'phone': '09120000000'}, {'phone': '09120000001'}]
        with patch.object(SmsCampaignSendView, '_send_provider_request') as send:
            self.assertEqual(self.send(recipients=recipients).status_code, 402)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, self.cost)
        self.assertFalse(CashflowTransaction.objects.filter(reference_type='sms_campaign_send').exists())
        send.assert_not_called()

    def test_failed_send_refunds_each_source_wallet(self):
        self.wallet.balance = self.cost / 2
        self.wallet.save()
        second = Wallet.objects.create(
            tenant=self.tenant, name='SMS 2', wallet_type=Wallet.WalletType.SMS,
            balance=self.cost / 2,
        )
        with patch.object(SmsCampaignSendView, '_send_provider_request', return_value=self.result(False)):
            self.assertEqual(self.send().status_code, 502)
        self.wallet.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(self.wallet.balance, self.cost / 2)
        self.assertEqual(second.balance, self.cost / 2)

    def test_exception_refunds_unsent_credit(self):
        with patch.object(SmsCampaignSendView, '_send_provider_request', side_effect=RuntimeError('provider')):
            with self.assertRaises(RuntimeError):
                self.send()
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, self.cost)

    def test_partial_failure_keeps_only_successful_cost(self):
        text = 'Hello [نام مشتری]'
        successful_cost = sms_cost_for_text('Hello A')
        failed_cost = sms_cost_for_text('Hello B')
        self.wallet.balance = successful_cost + failed_cost
        self.wallet.save()
        with patch.object(SmsCampaignSendView, '_send_provider_request', side_effect=[self.result(True), self.result(False)]):
            response = self.send(text, [
                {'phone': '09120000000', 'name': 'A'},
                {'phone': '09120000001', 'name': 'B'},
            ])
        self.wallet.refresh_from_db()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['success_count'], 1)
        self.assertEqual(response.data['failed_count'], 1)
        self.assertEqual(response.data['debited_amount'], successful_cost)
        self.assertEqual(self.wallet.balance, failed_cost)
