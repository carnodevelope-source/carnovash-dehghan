from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.auth.models import CarWash, SupportTicket, SupportTicketMessage


class SupportTicketAutoCloseTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.tenant = CarWash.objects.create(name='Auto Close Wash', slug='auto-close-wash')
        self.manager = user_model.objects.create_user(
            username='auto-close-manager',
            password='pass12345',
            phone='09128880001',
            role='manager',
            tenant=self.tenant,
        )

    def _ticket(self, *, last_message_at, status=SupportTicket.Status.OPEN):
        ticket = SupportTicket.objects.create(
            tenant=self.tenant,
            created_by=self.manager,
            subject='Support issue',
            message='Initial message',
            category=SupportTicket.Category.TECHNICAL,
            priority=SupportTicket.Priority.MEDIUM,
            status=status,
            last_message_at=last_message_at,
        )
        SupportTicketMessage.objects.create(ticket=ticket, sender=self.manager, body='Initial message')
        return ticket

    def test_command_closes_ticket_after_three_days_without_messages(self):
        old_ticket = self._ticket(last_message_at=timezone.now() - timedelta(days=3, minutes=1))
        fresh_ticket = self._ticket(last_message_at=timezone.now() - timedelta(days=2, hours=23))

        call_command('close_stale_support_tickets')

        old_ticket.refresh_from_db()
        fresh_ticket.refresh_from_db()
        self.assertEqual(old_ticket.status, SupportTicket.Status.CLOSED)
        self.assertIsNotNone(old_ticket.closed_at)
        self.assertEqual(fresh_ticket.status, SupportTicket.Status.OPEN)
        self.assertIsNone(fresh_ticket.closed_at)

    def test_ticket_list_auto_closes_stale_tickets_before_response(self):
        stale_ticket = self._ticket(last_message_at=timezone.now() - timedelta(days=4))
        self.client.force_authenticate(self.manager)

        response = self.client.get(reverse('support-tickets'))

        self.assertEqual(response.status_code, 200)
        row = next(item for item in response.data if item['id'] == stale_ticket.id)
        self.assertEqual(row['status'], SupportTicket.Status.CLOSED)

