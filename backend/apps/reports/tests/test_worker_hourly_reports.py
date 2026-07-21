from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.auth.models import CarWash
from apps.reports.models import WorkerPayoutTransaction
from apps.reports.views import _compute_worker_financials
from apps.vehicles.models import VehicleEntry, VehicleJob
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

    def test_worker_report_exposes_service_total_separate_from_share_and_tip(self):
        vehicle = VehicleEntry.objects.create(
            tenant=self.tenant,
            plate_number='11 A 111 11',
            plate_left='11',
            plate_letter='A',
            plate_mid='111',
            plate_right='11',
            car_model='Receipt Car',
            car_color='White',
            driver_name='Receipt Customer',
            driver_phone='09120001111',
            status=VehicleEntry.Status.RELEASED,
        )
        VehicleJob.objects.create(
            tenant=self.tenant,
            vehicle=vehicle,
            assigned_worker=self.worker,
            assigned_workers_snapshot=[{
                'id': self.worker.id,
                'name': 'Hourly Worker',
                'worker_share_percent': 100,
                'worker_share_amount': 50000,
                'tip_share_amount': 30000,
            }],
            worker_payment_type=VehicleJob.WorkerPaymentType.PERCENT,
            worker_payment_percent=10,
            services_total=170000,
            tip_amount=30000,
            final_total=200000,
            worker_share_amount=50000,
            carwash_share_amount=120000,
        )
        self.client.force_authenticate(self.manager)

        response = self.client.get(
            reverse('reports-dashboard'),
            {'worker_id': self.worker.id},
        )

        self.assertEqual(response.status_code, 200)
        row = response.data['worker_report'][0]
        self.assertEqual(row['service_total'], 170000.0)
        self.assertEqual(row['final_total_without_tip'], 170000.0)
        self.assertEqual(row['tip_amount'], 30000.0)
        self.assertEqual(row['worker_commission_percent'], 10.0)
        self.assertEqual(row['worker_share'], 17000.0)

    def test_insurance_start_month_is_treated_as_paid_and_balance_starts_next_month(self):
        self.worker.insurance_amount = Decimal('1000')
        self.worker.save(update_fields=['insurance_amount'])

        with patch('apps.reports.views._resolve_worker_insurance_start_month', return_value='1405/04'):
            start_month_state = _compute_worker_financials(self.worker, [], insurance_month='1405/04')
            next_month_state = _compute_worker_financials(self.worker, [], insurance_month='1405/05')

        self.assertEqual(start_month_state['insurance_total'], Decimal('0'))
        self.assertEqual(start_month_state['insurance_paid_total'], Decimal('0'))
        self.assertEqual(start_month_state['insurance_balance'], Decimal('0'))
        self.assertEqual(start_month_state['insurance_selected_month_balance'], Decimal('0'))
        self.assertEqual(start_month_state['insurance_due_start_month'], '1405/05')
        self.assertEqual(next_month_state['insurance_total'], Decimal('1000'))
        self.assertEqual(next_month_state['insurance_paid_total'], Decimal('0'))
        self.assertEqual(next_month_state['insurance_balance'], Decimal('1000'))
        self.assertEqual(next_month_state['insurance_selected_month_balance'], Decimal('1000'))

    def test_insurance_actual_payments_are_added_after_auto_paid_start_month(self):
        self.worker.insurance_amount = Decimal('1000')
        self.worker.save(update_fields=['insurance_amount'])
        WorkerPayoutTransaction.objects.create(
            tenant=self.tenant,
            worker=self.worker,
            kind=WorkerPayoutTransaction.Kind.INSURANCE_PAYMENT,
            reference_month='1405/05',
            amount=Decimal('400'),
        )

        with patch('apps.reports.views._resolve_worker_insurance_start_month', return_value='1405/04'):
            state = _compute_worker_financials(self.worker, [], insurance_month='1405/05')

        self.assertEqual(state['insurance_total'], Decimal('1000'))
        self.assertEqual(state['insurance_paid_total'], Decimal('400'))
        self.assertEqual(state['insurance_balance'], Decimal('600'))
        self.assertEqual(state['insurance_selected_month_paid_total'], Decimal('400'))
        self.assertEqual(state['insurance_selected_month_balance'], Decimal('600'))
