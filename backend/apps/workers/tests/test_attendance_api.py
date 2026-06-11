from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.auth.models import CarWash
from apps.workers.models import WorkerAttendance, WorkerProfile
from apps.workers.serializers import ensure_attendance_token


class AttendanceApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.tenant = CarWash.objects.create(name='Blue Wash', slug='blue-wash')
        self.manager = user_model.objects.create_user(
            username='manager1',
            password='pass12345',
            phone='09120000001',
            role='manager',
            tenant=self.tenant,
        )
        self.worker_user = user_model.objects.create_user(
            username='worker1',
            password='pass12345',
            phone='09120000002',
            role='worker',
            tenant=self.tenant,
            full_name='Ali Worker',
        )
        self.worker = WorkerProfile.objects.create(user=self.worker_user, tenant=self.tenant, load_status='normal')
        self.client = APIClient()

    def test_manager_dashboard_returns_worker_cards(self):
        WorkerAttendance.objects.create(
            worker=self.worker,
            tenant=self.tenant,
            event_type=WorkerAttendance.EventType.IN,
            event_at=timezone.now(),
            source='manager',
        )
        self.client.force_authenticate(self.manager)

        response = self.client.get(reverse('worker-attendance-dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['workers']), 1)
        self.assertEqual(response.data['workers'][0]['full_name'], 'Ali Worker')
        self.assertEqual(response.data['workers'][0]['current_status'], 'in')

    def test_public_attendance_link_registers_in_and_out(self):
        token = ensure_attendance_token(self.worker)
        endpoint = reverse('worker-attendance-public', args=[token])

        first = self.client.post(endpoint, {'event_type': 'in'}, format='json')
        second = self.client.post(endpoint, {'event_type': 'out'}, format='json')
        third = self.client.get(endpoint)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(third.status_code, 200)
        self.assertEqual(third.data['worker']['today_events_count'], 2)
        self.assertEqual(third.data['worker']['current_status'], 'out')
