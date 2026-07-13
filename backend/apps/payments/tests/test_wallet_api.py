from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.auth.models import CarWash
from apps.auth.models import CarWashFeaturePurchase
from apps.payments.models import CashflowTransaction, Wallet, WalletGatewayRequest


class WalletApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.tenant = CarWash.objects.create(name='Blue Wash', slug='blue-wash-wallet')
        self.manager = user_model.objects.create_user(
            username='wallet-manager',
            password='pass12345',
            phone='09129990001',
            role='manager',
            tenant=self.tenant,
        )
        self.wallet = Wallet.objects.create(
            tenant=self.tenant,
            name='Main Wallet',
            wallet_type=Wallet.WalletType.BANK,
            balance=500000,
            is_active=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.manager)

    def test_deposit_start_accepts_dynamic_amount(self):
        response = self.client.post(
            reverse('wallet-deposit-start'),
            {
                'wallet_id': self.wallet.id,
                'amount': 750000,
                'description': 'Dynamic top-up',
                'return_url': '/manager/wallet',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertIn('payment_url', response.data)
        self.assertTrue(
            WalletGatewayRequest.objects.filter(
                wallet=self.wallet,
                amount=750000,
                description='Dynamic top-up',
            ).exists()
        )

    def test_withdraw_rejects_amount_above_wallet_balance(self):
        response = self.client.post(
            reverse('wallet-withdraw'),
            {
                'wallet_id': self.wallet.id,
                'amount': 600000,
                'description': 'Too much',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.wallet.refresh_from_db()
        self.assertEqual(int(self.wallet.balance), 500000)

    def test_withdraw_can_transfer_between_wallets(self):
        sms_wallet = Wallet.objects.create(
            tenant=self.tenant,
            name='SMS Wallet',
            wallet_type=Wallet.WalletType.SMS,
            balance=0,
            is_active=True,
        )

        response = self.client.post(
            reverse('wallet-withdraw'),
            {
                'source_wallet_id': self.wallet.id,
                'destination_type': 'wallet',
                'destination_wallet_id': sms_wallet.id,
                'amount': 250000,
                'description': 'SMS top-up transfer',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.wallet.refresh_from_db()
        sms_wallet.refresh_from_db()
        self.assertEqual(int(self.wallet.balance), 250000)
        self.assertEqual(int(sms_wallet.balance), 250000)
        self.assertTrue(
            CashflowTransaction.objects.filter(
                tenant=self.tenant,
                wallet=self.wallet,
                direction=CashflowTransaction.Direction.OUT,
                reference_type='wallet_transfer_out',
                amount=250000,
            ).exists()
        )
        self.assertTrue(
            CashflowTransaction.objects.filter(
                tenant=self.tenant,
                wallet=sms_wallet,
                direction=CashflowTransaction.Direction.IN,
                reference_type='wallet_transfer_in',
                amount=250000,
            ).exists()
        )

    def test_withdraw_allows_sms_wallet_as_source_for_bank_destination(self):
        sms_wallet = Wallet.objects.create(
            tenant=self.tenant,
            name='SMS Wallet',
            wallet_type=Wallet.WalletType.SMS,
            balance=300000,
            is_active=True,
        )

        response = self.client.post(
            reverse('wallet-withdraw'),
            {
                'source_wallet_id': sms_wallet.id,
                'destination_type': 'bank',
                'amount': 100000,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        sms_wallet.refresh_from_db()
        self.assertEqual(int(sms_wallet.balance), 200000)

    def test_accounting_feature_option_purchase_is_available(self):
        self.wallet.balance = 10000000
        self.wallet.save(update_fields=['balance'])

        response = self.client.post(
            reverse('wallet-options'),
            {
                'wallet_id': self.wallet.id,
                'feature_key': 'accounting',
                'payment_plan': 'cash',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.wallet.refresh_from_db()
        self.assertTrue(
            CarWashFeaturePurchase.objects.filter(
                tenant=self.tenant,
                feature_key=CarWashFeaturePurchase.FeatureKey.ACCOUNTING,
                is_active=True,
            ).exists()
        )
        self.assertEqual(int(self.wallet.balance), 4000000)

    def test_installment_feature_option_purchase_debits_upfront_and_tracks_installments(self):
        self.wallet.balance = 10000000
        self.wallet.save(update_fields=['balance'])

        response = self.client.post(
            reverse('wallet-options'),
            {
                'wallet_id': self.wallet.id,
                'feature_key': 'cloud_storage',
                'payment_plan': 'installment',
                'upfront_amount': 1000000,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.wallet.refresh_from_db()
        purchase = CarWashFeaturePurchase.objects.get(
            tenant=self.tenant,
            feature_key=CarWashFeaturePurchase.FeatureKey.CLOUD_STORAGE,
        )
        self.assertTrue(purchase.is_active)
        self.assertEqual(purchase.payment_plan, CarWashFeaturePurchase.PaymentPlan.INSTALLMENT)
        self.assertEqual(int(purchase.paid_amount), 1000000)
        self.assertEqual(purchase.installment_months, 4)
        self.assertEqual(int(purchase.remaining_amount), 2000000)
        self.assertEqual(int(purchase.monthly_installment_amount), 500000)
        self.assertIsNotNone(purchase.next_installment_due_at)
        self.assertEqual(int(self.wallet.balance), 10000000 - int(purchase.paid_amount))

    def test_wallet_options_collects_due_installment_from_wallet_balance(self):
        self.wallet.balance = 2000000
        self.wallet.save(update_fields=['balance'])
        purchase = CarWashFeaturePurchase.objects.create(
            tenant=self.tenant,
            feature_key=CarWashFeaturePurchase.FeatureKey.CLOUD_STORAGE,
            is_active=True,
            payment_plan=CarWashFeaturePurchase.PaymentPlan.INSTALLMENT,
            total_amount=3000000,
            paid_amount=1000000,
            remaining_amount=1200000,
            installment_months=12,
            monthly_installment_amount=100000,
            next_installment_due_at=timezone.now() - timedelta(days=3),
        )

        response = self.client.get(reverse('wallet-options'))

        self.assertEqual(response.status_code, 200)
        self.wallet.refresh_from_db()
        purchase.refresh_from_db()
        self.assertEqual(int(self.wallet.balance), 1900000)
        self.assertEqual(int(purchase.paid_amount), 1100000)
        self.assertEqual(int(purchase.remaining_amount), 1100000)
        self.assertGreater(purchase.next_installment_due_at, timezone.now())

    def test_wallet_options_keeps_due_installment_when_wallet_balance_is_not_enough(self):
        self.wallet.balance = 50000
        self.wallet.save(update_fields=['balance'])
        purchase = CarWashFeaturePurchase.objects.create(
            tenant=self.tenant,
            feature_key=CarWashFeaturePurchase.FeatureKey.CLOUD_STORAGE,
            is_active=True,
            payment_plan=CarWashFeaturePurchase.PaymentPlan.INSTALLMENT,
            total_amount=3000000,
            paid_amount=1000000,
            remaining_amount=1200000,
            installment_months=12,
            monthly_installment_amount=100000,
            next_installment_due_at=timezone.now() - timedelta(days=3),
        )

        response = self.client.get(reverse('wallet-options'))

        self.assertEqual(response.status_code, 200)
        self.wallet.refresh_from_db()
        purchase.refresh_from_db()
        self.assertEqual(int(self.wallet.balance), 50000)
        self.assertEqual(int(purchase.paid_amount), 1000000)
        self.assertEqual(int(purchase.remaining_amount), 1200000)
        self.assertLessEqual(purchase.next_installment_due_at, timezone.now())

    def test_wallet_options_payload_reports_dynamic_feature_state(self):
        purchase = CarWashFeaturePurchase.objects.create(
            tenant=self.tenant,
            feature_key=CarWashFeaturePurchase.FeatureKey.ATTENDANCE,
            is_active=True,
            payment_plan=CarWashFeaturePurchase.PaymentPlan.INSTALLMENT,
            total_amount=2400000,
            paid_amount=600000,
            remaining_amount=1800000,
            installment_months=12,
            monthly_installment_amount=150000,
            next_installment_due_at=timezone.now() + timedelta(days=10),
        )

        response = self.client.get(reverse('wallet-options'))

        self.assertEqual(response.status_code, 200)
        option = next(item for item in response.data['options'] if item['feature_key'] == purchase.feature_key)
        self.assertEqual(option['status_label'], 'فعال شده')
        self.assertEqual(option['payment_plan_label'], 'پرداخت قسطی')
        self.assertEqual(int(option['paid_amount']), 600000)
        self.assertEqual(int(option['remaining_amount']), 1800000)
        self.assertEqual(int(option['next_installment_amount']), 150000)
        self.assertTrue(option['auto_charge_enabled'])
        self.assertGreater(option['progress_percent'], 0)

    def test_wallet_options_payload_marks_accounting_as_available(self):
        response = self.client.get(reverse('wallet-options'))

        self.assertEqual(response.status_code, 200)
        option = next(item for item in response.data['options'] if item['feature_key'] == CarWashFeaturePurchase.FeatureKey.ACCOUNTING)
        self.assertTrue(option['is_available'])
        self.assertEqual(int(option['cash_amount']), 6000000)
        self.assertEqual(int(option['installment_upfront_amount']), 1000000)
        self.assertEqual(option['installment_months'], 10)

    def test_excel_import_is_not_a_purchasable_wallet_option(self):
        response = self.client.get(reverse('wallet-options'))

        self.assertEqual(response.status_code, 200)
        feature_keys = {item['feature_key'] for item in response.data['options']}
        self.assertNotIn(CarWashFeaturePurchase.FeatureKey.EXCEL_IMPORT, feature_keys)

    def test_collect_due_feature_installments_command_debits_due_installments(self):
        self.wallet.balance = 300000
        self.wallet.save(update_fields=['balance'])
        purchase = CarWashFeaturePurchase.objects.create(
            tenant=self.tenant,
            feature_key=CarWashFeaturePurchase.FeatureKey.ACCOUNTING,
            is_active=True,
            payment_plan=CarWashFeaturePurchase.PaymentPlan.INSTALLMENT,
            total_amount=3600000,
            paid_amount=1200000,
            remaining_amount=900000,
            installment_months=12,
            monthly_installment_amount=150000,
            next_installment_due_at=timezone.now() - timedelta(days=1),
        )

        call_command('collect_due_feature_installments')

        self.wallet.refresh_from_db()
        purchase.refresh_from_db()
        self.assertEqual(int(self.wallet.balance), 150000)
        self.assertEqual(int(purchase.paid_amount), 1350000)
        self.assertEqual(int(purchase.remaining_amount), 750000)
        self.assertGreater(purchase.next_installment_due_at, timezone.now())

    def test_manual_feature_installment_payment_debits_wallet_and_moves_next_due(self):
        self.wallet.balance = 500000
        self.wallet.save(update_fields=['balance'])
        purchase = CarWashFeaturePurchase.objects.create(
            tenant=self.tenant,
            feature_key=CarWashFeaturePurchase.FeatureKey.CLOUD_STORAGE,
            is_active=True,
            payment_plan=CarWashFeaturePurchase.PaymentPlan.INSTALLMENT,
            total_amount=3000000,
            paid_amount=900000,
            remaining_amount=600000,
            installment_months=12,
            monthly_installment_amount=150000,
            next_installment_due_at=timezone.now() + timedelta(days=5),
        )
        old_due_at = purchase.next_installment_due_at

        response = self.client.post(
            reverse('wallet-options'),
            {
                'action': 'pay_installment',
                'feature_key': purchase.feature_key,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.wallet.refresh_from_db()
        purchase.refresh_from_db()
        self.assertEqual(int(self.wallet.balance), 350000)
        self.assertEqual(int(purchase.paid_amount), 1050000)
        self.assertEqual(int(purchase.remaining_amount), 450000)
        self.assertGreater(purchase.next_installment_due_at, old_due_at)
        self.assertTrue(
            CashflowTransaction.objects.filter(
                tenant=self.tenant,
                reference_type='feature_option_installment_manual',
                reference_id=purchase.id,
                amount=150000,
            ).exists()
        )
