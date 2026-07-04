from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from apps.auth.models import CarWash
from apps.notifications.models import NotificationLog
from apps.payments.models import Wallet


@override_settings(DEBUG=True, IRANPAYAMAK_API_KEY='', IRANPAYAMAK_LINE_NUMBER='')
class SimpleSmsSendTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.tenant = CarWash.objects.create(name='کارواش تست', slug='sms-debug')
        self.user = user_model.objects.create_user(
            username='sms-debug-user',
            password='pass12345',
            phone='09129990002',
            role='manager',
            tenant=self.tenant,
        )
        Wallet.objects.create(
            tenant=self.tenant,
            name='کیف پول پیامک',
            wallet_type=Wallet.WalletType.SMS,
            balance=500000,
            is_active=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_simple_sms_send_rejects_request_without_provider_credentials(self):
        response = self.client.post(
            reverse('notifications-sms-simple'),
            {
                'text': 'سلام تست پیامک',
                'recipients': ['09120000000'],
                'target_label': 'پیامک تکی تست',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('تنظیمات سرویس پیامک کامل نیست', str(response.data.get('detail', '')))
        self.assertFalse(
            NotificationLog.objects.filter(
                tenant=self.tenant,
                channel=NotificationLog.Channel.SMS,
                recipient='09120000000',
            ).exists()
        )
