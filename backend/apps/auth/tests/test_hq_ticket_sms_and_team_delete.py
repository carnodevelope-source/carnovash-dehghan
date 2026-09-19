from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from apps.auth.models import CarWash, SupportTicket
from apps.auth.support_tickets import (
    hq_ticket_alert_kind,
    notify_hq_alert_ticket_sms,
)


User = get_user_model()


class HqTicketSmsNotifyTests(TestCase):
    def setUp(self):
        cache.clear()
        self.tenant = CarWash.objects.create(name='SMS Wash', slug='sms-wash')
        self.support = User.objects.create_user(
            username='hq_sms_support',
            password='pass12345',
            phone='09121110001',
            role='admin',
            platform_role=User.PlatformRoles.HQ_SUPPORT,
            is_staff=True,
        )
        self.admin = User.objects.create_user(
            username='hq_sms_admin',
            password='pass12345',
            phone='09121110002',
            role='admin',
            platform_role=User.PlatformRoles.HQ_ADMIN,
            is_staff=True,
        )

    def test_alert_kind_for_payment_withdraw_registration(self):
        payment = SupportTicket.objects.create(
            tenant=self.tenant,
            subject='شارژ',
            message='wallet-card-payment\nکیف پول',
            status=SupportTicket.Status.OPEN,
        )
        withdraw = SupportTicket.objects.create(
            tenant=self.tenant,
            subject='برداشت',
            message='wallet-bank-withdrawal',
            status=SupportTicket.Status.OPEN,
        )
        registration = SupportTicket.objects.create(
            tenant=self.tenant,
            subject='ثبت نام',
            message='درخواست ثبت‌نام',
            status=SupportTicket.Status.OPEN,
            is_registration_request=True,
        )
        other = SupportTicket.objects.create(
            tenant=self.tenant,
            subject='عمومی',
            message='سوال عمومی',
            status=SupportTicket.Status.OPEN,
        )
        self.assertEqual(hq_ticket_alert_kind(payment), 'پرداخت')
        self.assertEqual(hq_ticket_alert_kind(withdraw), 'برداشت')
        self.assertEqual(hq_ticket_alert_kind(registration), 'ثبت‌نام')
        self.assertIsNone(hq_ticket_alert_kind(other))

    @override_settings(IRANPAYAMAK_API_KEY='k', IRANPAYAMAK_LINE_NUMBER='3000')
    @patch('apps.auth.support_tickets.send_provider_sms')
    def test_notify_sends_once_to_all_hq_phones(self, mock_send):
        mock_send.return_value = {'ok': True}
        ticket = SupportTicket.objects.create(
            tenant=self.tenant,
            subject='شارژ',
            message='wallet-card-payment\nکیف پول کارت به کارت',
            status=SupportTicket.Status.OPEN,
        )
        first = notify_hq_alert_ticket_sms(ticket)
        second = notify_hq_alert_ticket_sms(ticket)
        self.assertTrue(first.get('ok'))
        self.assertEqual(second.get('reason'), 'already_notified')
        self.assertEqual(mock_send.call_count, 1)
        _tenant, body, phones = mock_send.call_args[0]
        self.assertIn('تیکت پرداخت', body)
        self.assertIn('سامانه کارنوواش', body)
        self.assertCountEqual(phones, ['09121110001', '09121110002'])


class HqSupportDeleteTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='hq_del_admin',
            password='pass12345',
            phone='09123330001',
            role='admin',
            platform_role=User.PlatformRoles.HQ_ADMIN,
            is_staff=True,
        )
        self.support = User.objects.create_user(
            username='hq_del_support',
            password='pass12345',
            phone='09123330002',
            role='admin',
            platform_role=User.PlatformRoles.HQ_SUPPORT,
            is_staff=True,
        )
        self.client.force_authenticate(self.admin)

    def test_delete_removes_support_from_team_list(self):
        list_url = reverse('hq-team')
        before = self.client.get(list_url)
        self.assertEqual(before.status_code, 200)
        self.assertTrue(any(item['id'] == self.support.id for item in before.data))

        delete_url = reverse('hq-team-detail', kwargs={'pk': self.support.id})
        deleted = self.client.delete(delete_url)
        self.assertEqual(deleted.status_code, 200)
        self.assertTrue(deleted.data.get('soft_deleted'))

        after = self.client.get(list_url)
        self.assertEqual(after.status_code, 200)
        self.assertFalse(any(item['id'] == self.support.id for item in after.data))

        self.support.refresh_from_db()
        self.assertTrue(self.support.is_deleted)
        self.assertFalse(self.support.is_active)
