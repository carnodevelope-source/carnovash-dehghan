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
        self.worker.payment_type = WorkerProfile.PaymentType.PERCENT
        self.worker.default_commission_percent = 10
        self.worker.save(update_fields=['payment_type', 'default_commission_percent'])
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
                'worker_share_amount': 17000,
                'tip_share_amount': 30000,
            }],
            worker_payment_type=VehicleJob.WorkerPaymentType.PERCENT,
            worker_payment_percent=10,
            services_total=170000,
            products_total=0,
            discount_total=20000,
            tip_amount=30000,
            final_total=180000,
            worker_share_amount=17000,
            carwash_share_amount=153000,
        )
        self.client.force_authenticate(self.manager)

        response = self.client.get(
            reverse('reports-dashboard'),
            {'worker_id': self.worker.id},
        )

        self.assertEqual(response.status_code, 200)
        row = response.data['worker_report'][0]
        self.assertEqual(row['service_total'], 170000.0)
        self.assertEqual(row['final_total_without_tip'], 150000.0)
        self.assertEqual(row['tip_amount'], 30000.0)
        self.assertEqual(row['worker_commission_percent'], 10.0)
        self.assertEqual(row['worker_share'], 17000.0)
        summary = response.data['summary']
        self.assertEqual(summary['worker_total'], 17000.0)
        self.assertEqual(summary['worker_total'], response.data['selected_worker_summary']['wage_total'])
        self.assertEqual(summary['payable_worker_total'], response.data['selected_worker_summary']['payable_total'])
        self.assertEqual(
            summary['insurance_total'],
            response.data['selected_worker_summary']['insurance_selected_month_balance'],
        )

    def test_worker_share_prefers_snapshot_and_ignores_list_prices(self):
        from apps.vehicles.models import VehicleJobService

        self.worker.payment_type = WorkerProfile.PaymentType.PERCENT
        self.worker.default_commission_percent = 10
        self.worker.save(update_fields=['payment_type', 'default_commission_percent'])
        vehicle = VehicleEntry.objects.create(
            tenant=self.tenant,
            plate_number='22 B 222 22',
            plate_left='22',
            plate_letter='B',
            plate_mid='222',
            plate_right='22',
            car_model='Discount Car',
            car_color='Black',
            driver_name='Discount Customer',
            driver_phone='09120002222',
            status=VehicleEntry.Status.RELEASED,
        )
        job = VehicleJob.objects.create(
            tenant=self.tenant,
            vehicle=vehicle,
            assigned_worker=self.worker,
            assigned_workers_snapshot=[{
                'id': self.worker.id,
                'name': 'Hourly Worker',
                'worker_share_percent': 100,
                'worker_share_amount': 40000,
                'tip_share_amount': 5000,
            }],
            worker_payment_type=VehicleJob.WorkerPaymentType.PERCENT,
            worker_payment_percent=10,
            services_total=400000,
            products_total=0,
            discount_total=20000,
            tip_amount=50000,
            final_total=430000,
            worker_share_amount=40000,
            carwash_share_amount=360000,
        )
        VehicleJobService.objects.create(
            tenant=self.tenant,
            vehicle_job=job,
            custom_service_name='Wash',
            quantity=1,
            list_unit_price=420000,
            unit_price=400000,
            line_total=400000,
            discount_amount=20000,
        )
        self.client.force_authenticate(self.manager)

        response = self.client.get(
            reverse('reports-dashboard'),
            {'worker_id': self.worker.id},
        )

        self.assertEqual(response.status_code, 200)
        row = response.data['worker_report'][0]
        self.assertEqual(row['final_total_without_tip'], 380000.0)
        self.assertEqual(row['worker_share'], 40000.0)
        self.assertEqual(response.data['summary']['worker_total'], 40000.0)
        self.assertEqual(response.data['selected_worker_summary']['wage_total'], 40000.0)

    def test_worker_share_ignores_zero_snapshot_and_uses_job_total(self):
        """Snapshot amount 0 (assignment/release sync bug) must not zero out report share."""
        self.worker.payment_type = WorkerProfile.PaymentType.PERCENT
        self.worker.default_commission_percent = 35
        self.worker.save(update_fields=['payment_type', 'default_commission_percent'])
        vehicle = VehicleEntry.objects.create(
            tenant=self.tenant,
            plate_number='78 د 159 54',
            plate_left='78',
            plate_letter='د',
            plate_mid='159',
            plate_right='54',
            car_model='سوزوکی ویتارا',
            car_color='نوک مدادی',
            driver_name='طباطبایی',
            driver_phone='09133511500',
            status=VehicleEntry.Status.RELEASED,
        )
        VehicleJob.objects.create(
            tenant=self.tenant,
            vehicle=vehicle,
            assigned_worker=self.worker,
            assigned_workers_snapshot=[{
                'id': self.worker.id,
                'name': 'کامران شه بخش',
                'worker_share_percent': 100,
                'worker_share_amount': 0,
                'tip_share_amount': 0,
            }],
            worker_payment_type=VehicleJob.WorkerPaymentType.PERCENT,
            worker_payment_percent=35,
            worker_share_amount=Decimal('227500'),
            carwash_share_amount=Decimal('422500'),
            services_total=Decimal('650000'),
            final_total=Decimal('650000'),
            released_at=timezone.now(),
        )
        self.client.force_authenticate(self.manager)

        response = self.client.get(
            reverse('reports-dashboard'),
            {'worker_id': self.worker.id},
        )

        self.assertEqual(response.status_code, 200)
        row = response.data['worker_report'][0]
        self.assertEqual(row['worker_share'], 227500.0)
        self.assertEqual(response.data['summary']['worker_total'], 227500.0)

    def test_dashboard_sync_heals_zero_worker_share_from_commission_percent(self):
        self.worker.payment_type = WorkerProfile.PaymentType.PERCENT
        self.worker.default_commission_percent = 35
        self.worker.save(update_fields=['payment_type', 'default_commission_percent'])
        vehicle = VehicleEntry.objects.create(
            tenant=self.tenant,
            plate_number='33 C 333 33',
            plate_left='33',
            plate_letter='C',
            plate_mid='333',
            plate_right='33',
            car_model='Sync Car',
            car_color='Blue',
            driver_name='Sync Customer',
            driver_phone='09120003333',
            status=VehicleEntry.Status.RELEASED,
        )
        job = VehicleJob.objects.create(
            tenant=self.tenant,
            vehicle=vehicle,
            assigned_worker=self.worker,
            assigned_workers_snapshot=[{
                'id': self.worker.id,
                'name': 'Hourly Worker',
                'worker_share_percent': 100,
                'worker_share_amount': 0,
                'tip_share_amount': 0,
            }],
            worker_payment_type=VehicleJob.WorkerPaymentType.PERCENT,
            worker_payment_percent=0,
            worker_share_amount=Decimal('0'),
            carwash_share_amount=Decimal('650000'),
            services_total=Decimal('650000'),
            final_total=Decimal('650000'),
            released_at=timezone.now(),
        )
        self.client.force_authenticate(self.manager)

        response = self.client.get(
            reverse('reports-dashboard'),
            {'worker_id': self.worker.id, 'sync': '1'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['synced_jobs'], 1)
        row = response.data['worker_report'][0]
        self.assertEqual(row['worker_share'], 227500.0)
        job.refresh_from_db()
        self.assertEqual(job.worker_share_amount, Decimal('227500.00'))
        self.assertEqual(job.worker_payment_percent, Decimal('35.00'))
        self.assertEqual(job.assigned_workers_snapshot[0]['worker_share_amount'], 227500.0)

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

    def test_selected_insurance_month_kpi_uses_only_that_month_amount(self):
        """Selecting Mordad must show one month of insurance (settings amount), not cumulative months."""
        self.worker.insurance_amount = Decimal('8000000')
        self.worker.save(update_fields=['insurance_amount'])
        self.client.force_authenticate(self.manager)

        with patch('apps.reports.views._resolve_worker_insurance_start_month', return_value='1405/04'):
            response = self.client.get(
                reverse('reports-dashboard'),
                {'worker_id': self.worker.id, 'insurance_month': '1405/05'},
            )

        self.assertEqual(response.status_code, 200)
        summary = response.data['summary']
        selected = response.data['selected_worker_summary']
        self.assertEqual(selected['insurance_monthly_amount'], 8000000.0)
        self.assertEqual(selected['insurance_selected_month_balance'], 8000000.0)
        self.assertEqual(selected['insurance_selected_month_paid_total'], 0.0)
        self.assertEqual(summary['insurance_total'], 8000000.0)
        # Cumulative owed may be larger later, but KPI for selected month stays one month.
        self.assertEqual(selected['insurance_balance'], 8000000.0)

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
