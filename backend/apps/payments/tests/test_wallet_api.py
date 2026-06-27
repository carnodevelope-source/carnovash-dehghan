from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from apps.auth.models import CarWash
from apps.auth.models import CarWashFeaturePurchase
from apps.payments.models import Wallet, WalletGatewayRequest


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

    def test_cash_feature_option_purchase_debits_wallet_and_activates_feature(self):
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
        purchase = CarWashFeaturePurchase.objects.get(
            tenant=self.tenant,
            feature_key=CarWashFeaturePurchase.FeatureKey.ACCOUNTING,
        )
        self.assertTrue(purchase.is_active)
        self.assertEqual(purchase.payment_plan, CarWashFeaturePurchase.PaymentPlan.CASH)
        self.assertEqual(int(purchase.remaining_amount), 0)
        self.assertEqual(int(self.wallet.balance), 10000000 - int(purchase.total_amount))

    def test_installment_feature_option_purchase_debits_upfront_and_tracks_installments(self):
        self.wallet.balance = 10000000
        self.wallet.save(update_fields=['balance'])

        response = self.client.post(
            reverse('wallet-options'),
            {
                'wallet_id': self.wallet.id,
                'feature_key': 'cloud_storage',
                'payment_plan': 'installment',
                'upfront_amount': 800000,
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
        self.assertEqual(int(purchase.paid_amount), 800000)
        self.assertEqual(purchase.installment_months, 12)
        self.assertGreater(purchase.remaining_amount, 0)
        self.assertGreater(purchase.monthly_installment_amount, 0)
        self.assertIsNotNone(purchase.next_installment_due_at)
        self.assertEqual(int(self.wallet.balance), 10000000 - int(purchase.paid_amount))
