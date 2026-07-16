from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.auth.models import CarWash
from apps.workers.models import WorkerAttendance, WorkerProfile


class WorkerHourlyReportsTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.client = APIClient()
        self.tenant = CarWash.objects.create(name='Hourly Wash', slug='hourly-wash')
        self.manager = user_model.objects.create_user(
            username='hourly_manager',
            password='pass12345',
            phone='09129990001',
            role='manager',
            tenant=self.tenant,
        )
        self.worker_user = user_model.objects.create_user(
            username='hourly_worker',
            password='pass12345',
            phone='09129990002',
            role='worker',
            tenant=self.tenant,
            full_name='Hourly Worker',
        )
        self.worker = WorkerProfile.objects.create(
            user=self.worker_user,
            tenant=self.tenant,
            payment_type=WorkerProfile.PaymentType.HOURLY,
            default_hourly_wage=100000,
        )

    def test_selected_hourly_worker_wage_uses_attendance_hours(self):
        start_at = timezone.now() - timedelta(hours=3)
        end_at = start_at + timedelta(hours=2)
        WorkerAttendance.objects.create(
            worker=self.worker,
            tenant=self.tenant,
            event_type=WorkerAttendance.EventType.IN,
            event_at=start_at,
            source='manager',
        )
        WorkerAttendance.objects.create(
            worker=self.worker,
            tenant=self.tenant,
            event_type=WorkerAttendance.EventType.OUT,
            event_at=end_at,
            source='manager',
        )
        self.client.force_authenticate(self.manager)

        response = self.client.get(
            reverse('reports-dashboard'),
            {'worker_id': self.worker.id},
        )

        self.assertEqual(response.status_code, 200)
        summary = response.data['selected_worker_summary']
        self.assertEqual(summary['payment_type'], WorkerProfile.PaymentType.HOURLY)
        self.assertEqual(summary['attendance_minutes'], 120)
        self.assertEqual(summary['attendance_hours'], 2.0)
        self.assertEqual(summary['hourly_wage'], 100000.0)
        self.assertEqual(summary['wage_total'], 200000.0)
        self.assertEqual(summary['payable_total'], 200000.0)
