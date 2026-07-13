from django.contrib.auth import get_user_model
from django.urls import reverse
from datetime import timedelta
from django.utils import timezone
from unittest.mock import patch
from rest_framework.test import APIClient, APITestCase

from apps.auth.models import CarWash, CarWashFeaturePurchase
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

    def test_attendance_allows_free_tier_up_to_five_workers(self):
        self.client.force_authenticate(self.manager)

        response = self.client.get(reverse('worker-attendance-dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['summary']['attendance_free_workers_limit'], 5)
        self.assertEqual(response.data['workers'][0]['attendance_enabled'], True)

    def test_attendance_blocks_sixth_worker_without_purchase(self):
        user_model = get_user_model()
        workers = [self.worker]
        for index in range(2, 7):
            worker_user = user_model.objects.create_user(
                username=f'worker{index}',
                password='pass12345',
                phone=f'091200001{index:02d}',
                role='worker',
                tenant=self.tenant,
                full_name=f'Worker {index}',
            )
            workers.append(WorkerProfile.objects.create(user=worker_user, tenant=self.tenant))

        blocked_worker = workers[-1]
        self.client.force_authenticate(self.manager)

        dashboard = self.client.get(reverse('worker-attendance-dashboard'))
        create_event = self.client.post(
            reverse('worker-attendance-event-create'),
            {'worker_id': blocked_worker.id, 'event_type': 'in'},
            format='json',
        )
        public = self.client.get(reverse('worker-attendance-public', args=[ensure_attendance_token(blocked_worker)]))

        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(create_event.status_code, 403)
        self.assertEqual(public.status_code, 403)
        self.assertEqual(create_event.data['code'], 'attendance_worker_limit_reached')
        blocked_card = next(item for item in dashboard.data['workers'] if item['id'] == blocked_worker.id)
        self.assertEqual(blocked_card['attendance_enabled'], False)

    def test_attendance_purchase_removes_worker_limit(self):
        user_model = get_user_model()
        workers = [self.worker]
        for index in range(2, 7):
            worker_user = user_model.objects.create_user(
                username=f'paid_worker{index}',
                password='pass12345',
                phone=f'091211001{index:02d}',
                role='worker',
                tenant=self.tenant,
                full_name=f'Paid Worker {index}',
            )
            workers.append(WorkerProfile.objects.create(user=worker_user, tenant=self.tenant))
        blocked_worker = workers[-1]
        CarWashFeaturePurchase.objects.create(
            tenant=self.tenant,
            feature_key=CarWashFeaturePurchase.FeatureKey.ATTENDANCE,
            is_active=True,
        )
        self.client.force_authenticate(self.manager)

        dashboard = self.client.get(reverse('worker-attendance-dashboard'))
        create_event = self.client.post(
            reverse('worker-attendance-event-create'),
            {'worker_id': blocked_worker.id, 'event_type': 'in'},
            format='json',
        )

        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(create_event.status_code, 201)

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

    @patch('apps.workers.views.send_user_credentials_sms')
    def test_worker_create_sends_credentials_sms(self, mock_send_credentials_sms):
        self.client.force_authenticate(self.manager)

        response = self.client.post(
            reverse('worker-list-create'),
            {
                'full_name': 'New Operator',
                'username': 'new-operator',
                'password': 'operator-pass-123',
                'phone': '09120000999',
                'role': 'operator',
                'is_available': True,
                'payment_type': 'percent',
                'payment_value': 30,
                'tip_share_percent': 50,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        mock_send_credentials_sms.assert_called_once()
        _, kwargs = mock_send_credentials_sms.call_args
        self.assertEqual(kwargs['tenant'], self.tenant)
        self.assertEqual(kwargs['tenant_name'], self.tenant.name)
        self.assertEqual(kwargs['phone'], '09120000999')
        self.assertEqual(kwargs['username'], 'new-operator')
        self.assertEqual(kwargs['password'], 'operator-pass-123')
        self.assertEqual(kwargs['role'], 'operator')
        self.assertEqual(kwargs['template_code'], 'worker_credentials')

    def test_worker_create_rejects_existing_manager_phone(self):
        self.client.force_authenticate(self.manager)

        response = self.client.post(
            reverse('worker-list-create'),
            {
                'full_name': 'Shadow Manager',
                'username': 'shadow-manager',
                'password': 'operator-pass-123',
                'phone': self.manager.phone,
                'role': 'operator',
                'is_available': True,
                'payment_type': 'percent',
                'payment_value': 30,
                'tip_share_percent': 50,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.manager.refresh_from_db()
        self.assertEqual(self.manager.role, 'manager')
        self.assertEqual(response.data['phone'][0], 'این شماره موبایل قبلا ثبت شده است.')

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
