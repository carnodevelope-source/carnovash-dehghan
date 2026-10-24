from datetime import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.auth.models import CarWash
from apps.payments.models import Payment
from apps.vehicles.models import VehicleEntry


class ReleaseDayTests(APITestCase):
    def setUp(self):
        self.tenant = CarWash.objects.create(name='Release day', slug='release-day')
        self.user = get_user_model().objects.create_user(
            username='release-day', password='test-pass', role='manager', tenant=self.tenant,
        )
        self.client.force_authenticate(self.user)
        self.admitted = timezone.make_aware(datetime(2026, 10, 22, 23, 50))
        self.released = timezone.make_aware(datetime(2026, 10, 23, 0, 10))
        self.vehicle = VehicleEntry.objects.create(
            tenant=self.tenant, plate_number='12 B 345 67',
            status=VehicleEntry.Status.RELEASED, released_at=self.released,
        )
        VehicleEntry.objects.filter(pk=self.vehicle.pk).update(check_in_at=self.admitted)
        payment = Payment.objects.create(
            tenant=self.tenant, vehicle_entry=self.vehicle, method=Payment.Method.CASH,
            status=Payment.Status.SUCCESS, amount=Decimal('500000'), paid_at=self.admitted,
        )
        Payment.objects.filter(pk=payment.pk).update(created_at=self.admitted)

    def test_board_counts_completed_vehicle_and_amount_on_release_day(self):
        for day, expected_count in [('2026-10-22', 0), ('2026-10-23', 1)]:
            for status_filter in ({}, {'status': 'released'}):
                with self.subTest(day=day, status=status_filter):
                    response = self.client.get(reverse('vehicle-list-create'), {
                        'date_start': day, 'date_end': day, **status_filter,
                    })
                    self.assertEqual(response.status_code, 200)
                    rows = response.data
                    if isinstance(rows, dict):
                        rows = rows['results']
                    self.assertEqual(len(rows), expected_count)

    def test_revenue_total_and_display_date_follow_release(self):
        for day, expected_total in [('2026-10-22', 0), ('2026-10-23', 500000)]:
            response = self.client.get(reverse('reports-dashboard'), {'start': day, 'end': day})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['section_totals']['revenue']['revenue_total'], expected_total)
            rows = response.data['revenue_report']
            self.assertEqual(len(rows), int(bool(expected_total)))
            if rows:
                self.assertEqual(rows[0]['created_at'], self.released)

    def test_active_vehicle_still_uses_admission_date(self):
        VehicleEntry.objects.filter(pk=self.vehicle.pk).update(
            status=VehicleEntry.Status.READY_TO_SETTLE, released_at=None,
        )
        response = self.client.get(reverse('vehicle-list-create'), {
            'date_start': '2026-10-22', 'date_end': '2026-10-22',
        })
        self.assertEqual(response.status_code, 200)
        rows = response.data
        if isinstance(rows, dict):
            rows = rows['results']
        self.assertEqual(len(rows), 1)
