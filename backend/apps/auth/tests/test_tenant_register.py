from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.auth.models import CarWash, PendingTenantRegistration, SupportTicket
from apps.notifications.models import NotificationLog


@override_settings(
    IRANPAYAMAK_API_KEY='test-api-key',
    IRANPAYAMAK_LINE_NUMBER='30001234',
    IRANPAYAMAK_BASE_URL='https://api.iranpayamak.com',
)
class TenantRegisterTests(APITestCase):
    def _document(self, name='business-license.txt'):
        return SimpleUploadedFile(name, b'business-doc', content_type='text/plain')

    def test_register_creates_pending_carwash_manager_and_support_ticket(self):
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
                'business_identity_documents': [self._document()],
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, 201)
        tenant = CarWash.objects.get(name='کارواش ستاره')
        manager = get_user_model().objects.get(username='setare-manager')
        ticket = SupportTicket.objects.get(tenant=tenant, is_registration_request=True)
        registration = PendingTenantRegistration.objects.get(tenant=tenant)

        self.assertFalse(tenant.is_active)
        self.assertFalse(manager.is_active)
        self.assertEqual(manager.tenant_id, tenant.id)
        self.assertEqual(ticket.created_by_id, manager.id)
        self.assertEqual(registration.support_ticket_id, ticket.id)
        self.assertEqual(registration.status, PendingTenantRegistration.Status.PENDING)
        self.assertEqual(response.data['registration']['status'], PendingTenantRegistration.Status.PENDING)
        self.assertEqual(response.data['registration']['ticket_id'], ticket.id)
        self.assertEqual(ticket.attachments.count(), 1)

    def test_pending_registration_cannot_log_in_before_support_approval(self):
        self.client.post(
            reverse('tenant-register'),
            {
                'carwash_name': 'کارواش معلق',
                'manager_first_name': 'ندا',
                'manager_last_name': 'ملکی',
                'manager_username': 'pending-manager',
                'manager_phone': '09120000001',
                'manager_password': 'pass12345',
                'business_identity_documents': [self._document('id-card.txt')],
            },
            format='multipart',
        )

        login_response = self.client.post(
            reverse('login'),
            {'username': 'pending-manager', 'password': 'pass12345'},
            format='json',
        )

        self.assertEqual(login_response.status_code, 400)
        self.assertIn('هنوز توسط پشتیبانی تایید نشده', str(login_response.data))

    @patch('apps.auth.sms.send_provider_sms')
    def test_hq_can_approve_registration_and_send_sms(self, mock_send_provider_sms):
        mock_send_provider_sms.return_value = {
            'ok': True,
            'message': 'پیامک با موفقیت در صف ارسال قرار گرفت.',
            'provider_status': 200,
            'provider_data': {'status': 'success', 'data': {'id': 'provider-tenant-1'}},
            'provider_id': 'provider-tenant-1',
            'raw_body': '{"status":"success","data":{"id":"provider-tenant-1"}}',
            'payload': {'line_number': '30001234', 'recipients': ['09120000002']},
        }
        self.client.post(
            reverse('tenant-register'),
            {
                'carwash_name': 'کارواش تایید',
                'carwash_address': 'قم',
                'manager_first_name': 'مهدی',
                'manager_last_name': 'کریمی',
                'manager_username': 'approve-manager',
                'manager_phone': '09120000002',
                'manager_password': 'pass12345',
                'business_identity_documents': [self._document('permit.txt')],
            },
            format='multipart',
        )
        tenant = CarWash.objects.get(name='کارواش تایید')
        ticket = SupportTicket.objects.get(tenant=tenant, is_registration_request=True)
        hq_user = get_user_model().objects.create_user(
            username='hq-admin',
            password='adminpass123',
            phone='09129999999',
            role='admin',
            platform_role='hq_admin',
            is_staff=True,
            is_active=True,
        )
        self.client.force_authenticate(user=hq_user)

        response = self.client.post(reverse('hq-ticket-approve-registration', args=[ticket.id]), {}, format='json')

        self.assertEqual(response.status_code, 200)
        tenant.refresh_from_db()
        manager = get_user_model().objects.get(username='approve-manager')
        registration = PendingTenantRegistration.objects.get(tenant=tenant)
        ticket.refresh_from_db()

        self.assertTrue(tenant.is_active)
        self.assertTrue(manager.is_active)
        self.assertEqual(registration.status, PendingTenantRegistration.Status.APPROVED)
        self.assertEqual(ticket.status, SupportTicket.Status.CLOSED)
        self.assertTrue(response.data['sms']['ok'])
        self.assertTrue(
            NotificationLog.objects.filter(
                tenant=tenant,
                template_code='tenant_registration_credentials',
                status=NotificationLog.Status.SENT,
                recipient='09120000002',
                provider_message_id='provider-tenant-1',
            ).exists()
        )
        mock_send_provider_sms.assert_called_once()
