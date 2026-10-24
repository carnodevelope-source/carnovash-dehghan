from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.auth.models import CarWash, SupportTicket, SupportTicketMessage
from apps.auth.views import HqTicketDetailView, HqTicketListView


class HqTicketCompletenessTests(TestCase):
    def setUp(self):
        self.tenant = CarWash.objects.create(name='Ticket review', slug='ticket-review')
        self.admin = get_user_model().objects.create_user(
            username='ticket-admin', role='admin', platform_role='hq_admin',
            is_staff=True, is_superuser=True,
        )

    def fetch(self, params=None):
        request = APIRequestFactory().get('/api/auth/hq/tickets/', params or {})
        force_authenticate(request, self.admin)
        return HqTicketListView.as_view()(request)

    def test_list_includes_more_than_300_tickets(self):
        SupportTicket.objects.bulk_create([
            SupportTicket(tenant=self.tenant, subject=f'Ticket {i}', last_message_at=timezone.now())
            for i in range(305)
        ])
        response = self.fetch()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 305)

    def test_latest_message_and_count_are_complete(self):
        ticket = SupportTicket.objects.create(
            tenant=self.tenant, subject='Conversation', message='Original', last_message_at=timezone.now(),
        )
        SupportTicketMessage.objects.create(ticket=ticket, sender=self.admin, body='First')
        SupportTicketMessage.objects.create(ticket=ticket, sender=self.admin, body='Latest')
        row = self.fetch().data[0]
        self.assertEqual(row['messages_count'], 2)
        self.assertEqual(row['last_message_preview'], 'Latest')

    def test_filter_keeps_matching_tickets_beyond_300(self):
        SupportTicket.objects.bulk_create([
            SupportTicket(tenant=self.tenant, subject=f'Ticket {i}', last_message_at=timezone.now())
            for i in range(305)
        ])
        response = self.fetch({'q': 'Ticket 0'})
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['subject'], 'Ticket 0')

    def change_status(self, ticket, status, user=None):
        request = APIRequestFactory().patch('/ticket/', {'status': status}, format='json')
        force_authenticate(request, user or self.admin)
        return HqTicketDetailView.as_view()(request, pk=ticket.pk)

    def test_close_and_reopen_without_reply(self):
        ticket = SupportTicket.objects.create(tenant=self.tenant, subject='Status test')
        self.assertEqual(self.change_status(ticket, 'closed').status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'closed')
        self.assertIsNotNone(ticket.closed_at)
        self.assertEqual(ticket.messages.count(), 0)
        self.assertIsNone(ticket.first_response_at)
        self.assertEqual(self.change_status(ticket, 'open').status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'open')
        self.assertIsNone(ticket.closed_at)

    def test_invalid_status_does_not_change_ticket(self):
        ticket = SupportTicket.objects.create(tenant=self.tenant, subject='Status test')
        self.assertEqual(self.change_status(ticket, 'invalid').status_code, 400)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'open')

    def test_tenant_cannot_change_hq_status(self):
        user = get_user_model().objects.create_user(username='tenant-status', tenant=self.tenant, role='manager')
        ticket = SupportTicket.objects.create(tenant=self.tenant, subject='Status test')
        self.assertEqual(self.change_status(ticket, 'closed', user).status_code, 403)
