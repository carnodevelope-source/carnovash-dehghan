from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from apps.vehicles.models import VehicleEntry, VehicleJob
from apps.auth.models import CarWash
from apps.reports.models import WorkerPayoutTransaction
from apps.reports.monthly_wages import accrue_monthly_wages_for_day
from apps.reports.views import _worker_monthly_wage_for_month
from apps.workers.models import WorkerProfile


class WorkerMonthlyWageTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()

        self.tenant = CarWash.objects.create(
            name='Monthly Wash',
            slug='monthly-wash',
        )

        self.worker_user = user_model.objects.create_user(
            username='monthly_worker',
            password='pass12345',
            phone='09129990100',
            role='worker',
            tenant=self.tenant,
            full_name='Monthly Worker',
        )

        self.worker = WorkerProfile.objects.create(
            user=self.worker_user,
            tenant=self.tenant,
            payment_type=WorkerProfile.PaymentType.MONTHLY,
            default_monthly_wage=Decimal('20000000'),
            started_at=date(2026, 10, 12),  # 20 Mehr 1405
        )

    def test_monthly_worker_gets_zero_share_from_job(self):
        vehicle = VehicleEntry.objects.create(
            tenant=self.tenant,
            plate_number='55 M 555 55',
            plate_left='55',
            plate_letter='M',
            plate_mid='555',
            plate_right='55',
            car_model='Monthly Car',
            car_color='White',
            driver_name='Monthly Customer',
            driver_phone='09120005555',
            status=VehicleEntry.Status.RELEASED,
        )

        job = VehicleJob.objects.create(
            tenant=self.tenant,
            vehicle=vehicle,
            assigned_worker=self.worker,
            assigned_workers_snapshot=[{
                'id': self.worker.id,
                'name': 'Monthly Worker',
                'worker_share_percent': 100,
                'worker_share_amount': 500000,
                'tip_share_amount': 0,
            }],
            worker_payment_type=VehicleJob.WorkerPaymentType.MONTHLY,
            worker_payment_percent=Decimal('0'),
            worker_payment_fixed=Decimal('0'),
            worker_share_amount=Decimal('500000'),
            carwash_share_amount=Decimal('500000'),
            services_total=Decimal('1000000'),
            final_total=Decimal('1000000'),
        )

        from apps.reports.views import _job_worker_share_for

        share = _job_worker_share_for(
            job,
            self.worker.id,
        )

        self.assertEqual(share, Decimal('0'))

    def test_partial_first_month_excludes_start_day(self):
        amount = _worker_monthly_wage_for_month(
            self.worker,
            '1405/07',
        )

        self.assertEqual(
            amount,
            Decimal('6666666.67'),
        )

    def test_next_month_gets_full_monthly_wage(self):
        amount = _worker_monthly_wage_for_month(
            self.worker,
            '1405/08',
        )

        self.assertEqual(
            amount,
            Decimal('20000000'),
        )

    def test_accrual_is_not_created_before_end_of_month(self):
        created = accrue_monthly_wages_for_day(
            date(2026, 10, 21)
        )

        self.assertEqual(created, 0)

        self.assertFalse(
            WorkerPayoutTransaction.objects.filter(
                worker=self.worker,
                kind=WorkerPayoutTransaction.Kind.MONTHLY_WAGE_ACCRUAL,
            ).exists()
        )

    def test_accrual_is_created_on_last_day_of_month(self):
        created = accrue_monthly_wages_for_day(
            date(2026, 10, 22)
        )

        self.assertEqual(created, 1)

        transaction = WorkerPayoutTransaction.objects.get(
            worker=self.worker,
            kind=WorkerPayoutTransaction.Kind.MONTHLY_WAGE_ACCRUAL,
            reference_month='1405/07',
        )

        self.assertEqual(
            transaction.amount,
            Decimal('6666666.67'),
        )

        self.assertEqual(
            transaction.accrual_key,
            f'monthly-wage:{self.worker.id}:1405/07',
        )

    def test_monthly_accrual_is_idempotent(self):
        first = accrue_monthly_wages_for_day(
            date(2026, 10, 22)
        )

        second = accrue_monthly_wages_for_day(
            date(2026, 10, 22)
        )

        self.assertEqual(first, 1)
        self.assertEqual(second, 0)

        self.assertEqual(
            WorkerPayoutTransaction.objects.filter(
                worker=self.worker,
                kind=WorkerPayoutTransaction.Kind.MONTHLY_WAGE_ACCRUAL,
                reference_month='1405/07',
            ).count(),
            1,
        )

    def test_partial_first_month_in_31_day_month(self):
        # 20 Farvardin 1405 = 2026-04-09
        self.worker.started_at = date(2026, 4, 9)
        self.worker.save(update_fields=['started_at'])

        amount = _worker_monthly_wage_for_month(
            self.worker,
            '1405/01',
        )

        expected = (
            Decimal('20000000') * Decimal('11') / Decimal('31')
        ).quantize(Decimal('0.01'))

        self.assertEqual(amount, expected)

    def test_esfand_has_29_days_in_normal_year(self):
        from apps.reports.views import _jalali_month_days

        self.assertEqual(
            _jalali_month_days(1405, 12),
            29,
        )


    def test_esfand_has_30_days_in_leap_year(self):
        from apps.reports.views import _jalali_month_days

        self.assertEqual(
            _jalali_month_days(1403, 12),
            30,
        )

    def test_new_worker_payment_settings_are_persisted(self):
        from types import SimpleNamespace
        from apps.workers.serializers import WorkerProfileCreateUpdateSerializer

        for index, (payment_type, field) in enumerate([
            ('monthly', 'default_monthly_wage'),
            ('hourly', 'default_hourly_wage'),
            ('fixed', 'default_fixed_wage'),
        ]):
            with self.subTest(payment_type=payment_type):
                serializer = WorkerProfileCreateUpdateSerializer(
                    data={
                        'full_name': 'New Worker',
                        'phone': f'0912999020{index}',
                        'payment_type': payment_type,
                        'payment_value': '150000',
                    },
                    context={'request': SimpleNamespace(user=self.worker_user)},
                )
                self.assertTrue(serializer.is_valid(), serializer.errors)
                profile = serializer.save()
                profile.refresh_from_db()
                self.assertEqual(profile.payment_type, payment_type)
                self.assertEqual(getattr(profile, field), Decimal('150000'))
