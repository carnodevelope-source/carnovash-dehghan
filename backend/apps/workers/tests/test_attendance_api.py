from django.contrib.auth import get_user_model
from django.urls import reverse
from datetime import timedelta
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

    def test_worker_list_uses_attendance_queue_and_assignment_tail(self):
        user_model = get_user_model()
        second_user = user_model.objects.create_user(
            username='worker2',
            password='pass12345',
            phone='09120000003',
            role='worker',
            tenant=self.tenant,
            full_name='Earlier Assigned',
        )
        second_worker = WorkerProfile.objects.create(
            user=second_user,
            tenant=self.tenant,
            last_assigned_at=timezone.now() - timedelta(minutes=10),
        )
        third_user = user_model.objects.create_user(
            username='worker3',
            password='pass12345',
            phone='09120000004',
            role='worker',
            tenant=self.tenant,
            full_name='Absent Worker',
        )
        WorkerProfile.objects.create(user=third_user, tenant=self.tenant)

        WorkerAttendance.objects.create(
            worker=self.worker,
            tenant=self.tenant,
            event_type=WorkerAttendance.EventType.IN,
            event_at=timezone.now() - timedelta(hours=2),
            source='manager',
        )
        WorkerAttendance.objects.create(
            worker=second_worker,
            tenant=self.tenant,
            event_type=WorkerAttendance.EventType.IN,
            event_at=timezone.now() - timedelta(hours=3),
            source='manager',
        )
        self.client.force_authenticate(self.manager)

        response = self.client.get(reverse('worker-list-create'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in response.data[:2]], [self.worker.id, second_worker.id])
        self.assertEqual(response.data[0]['current_status'], 'in')
        self.assertIsNotNone(response.data[0]['queue_position_at'])

    def test_vehicle_assignment_moves_all_selected_workers_to_tail(self):
        user_model = get_user_model()
        second_user = user_model.objects.create_user(
            username='worker4',
            password='pass12345',
            phone='09120000005',
            role='worker',
            tenant=self.tenant,
            full_name='Second Worker',
        )
        second_worker = WorkerProfile.objects.create(user=second_user, tenant=self.tenant)
        self.client.force_authenticate(self.manager)

        response = self.client.post(
            reverse('vehicle-list-create'),
            {
                'plate_number': '12 ب 345 67',
                'plate_left': '12',
                'plate_letter': 'ب',
                'plate_mid': '345',
                'plate_right': '67',
                'car_model': 'Test Car',
                'car_color': 'White',
                'driver_name': 'Test Driver',
                'driver_phone': '09120000111',
                'status': 'ready_to_settle',
                'worker_id': self.worker.id,
                'staff_members': [
                    {'id': self.worker.id, 'name': 'Ali Worker', 'worker_share_percent': 50},
                    {'id': second_worker.id, 'name': 'Second Worker', 'worker_share_percent': 50},
                ],
                'services': [
                    {'title': 'Wash', 'price': 1000, 'discount_amount': 0},
                ],
                'share': {'type': 'percent', 'value': 40},
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.worker.refresh_from_db()
        second_worker.refresh_from_db()
        self.assertIsNotNone(self.worker.last_assigned_at)
        self.assertIsNotNone(second_worker.last_assigned_at)
