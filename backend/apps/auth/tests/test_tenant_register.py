from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.auth.models import CarWash
from apps.notifications.models import NotificationLog


@override_settings(
    IRANPAYAMAK_API_KEY='test-api-key',
    IRANPAYAMAK_LINE_NUMBER='30001234',
    IRANPAYAMAK_BASE_URL='https://api.iranpayamak.com',
)
class TenantRegisterTests(APITestCase):
    @patch('apps.auth.sms.send_provider_sms')
    def test_register_creates_carwash_manager_and_returns_credentials(self, mock_send_provider_sms):
        mock_send_provider_sms.return_value = {
            'ok': True,
            'message': 'پیامک با موفقیت در صف ارسال قرار گرفت.',
            'provider_status': 200,
            'provider_data': {'status': 'success', 'data': {'id': 'provider-tenant-1'}},
            'provider_id': 'provider-tenant-1',
            'raw_body': '{"status":"success","data":{"id":"provider-tenant-1"}}',
            'payload': {'line_number': '30001234', 'recipients': ['09120000000']},
        }

        response = self.client.post(
            reverse('tenant-register'),
            {
                'carwash_name': 'کارواش ستاره',
                'carwash_address': 'تهران، خیابان آزادی',
                'manager_first_name': 'علی',
                'manager_last_name': 'رضایی',
                'manager_username': 'setare-manager',
                'manager_phone': '09120000000',
                'manager_password': 'pass12345',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        tenant = CarWash.objects.get(name='کارواش ستاره')
        manager = get_user_model().objects.get(username='setare-manager')

        self.assertEqual(tenant.address, 'تهران، خیابان آزادی')
        self.assertEqual(manager.tenant_id, tenant.id)
        self.assertEqual(manager.first_name, 'علی')
        self.assertEqual(manager.last_name, 'رضایی')
        self.assertEqual(response.data['credentials']['username'], 'setare-manager')
        self.assertEqual(response.data['credentials']['password'], 'pass12345')
        self.assertTrue(response.data['sms']['ok'])
        self.assertTrue(
            NotificationLog.objects.filter(
                tenant=tenant,
                template_code='tenant_registration_credentials',
                status=NotificationLog.Status.SENT,
                recipient='09120000000',
                provider_message_id='provider-tenant-1',
            ).exists()
        )
        mock_send_provider_sms.assert_called_once()
