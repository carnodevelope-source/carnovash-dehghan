from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.auth.models import CarWash
from apps.reports.views import _reports_plate_match_q
from apps.vehicles.models import VehicleEntry


class ReportsPlateFilterTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.client = APIClient()
        self.tenant = CarWash.objects.create(name='Plate Filter Wash', slug='plate-filter-wash')
        self.manager = user_model.objects.create_user(
            username='plate_filter_manager',
            password='pass12345',
            phone='09128880001',
            role='manager',
            tenant=self.tenant,
        )
        self.client.force_authenticate(self.manager)
        now = timezone.now()

        self.v_a = VehicleEntry.objects.create(
            tenant=self.tenant,
            plate_number='12 ب 345 67',
            plate_left='12',
            plate_letter='ب',
            plate_mid='345',
            plate_right='67',
            car_model='Pride',
            driver_name='Ali',
            status=VehicleEntry.Status.RELEASED,
            released_at=now,
        )
        self.v_b = VehicleEntry.objects.create(
            tenant=self.tenant,
            plate_number='12 س 999 10',
            plate_left='12',
            plate_letter='س',
            plate_mid='999',
            plate_right='10',
            car_model='Samand',
            driver_name='Sara',
            status=VehicleEntry.Status.RELEASED,
            released_at=now,
        )
        self.v_c = VehicleEntry.objects.create(
            tenant=self.tenant,
            plate_number='98 ب 345 11',
            plate_left='98',
            plate_letter='ب',
            plate_mid='345',
            plate_right='11',
            car_model='Peugeot',
            driver_name='Reza',
            status=VehicleEntry.Status.RELEASED,
            released_at=now,
        )

    def _plates(self, **params):
        response = self.client.get(reverse('reports-dashboard'), params)
        self.assertEqual(response.status_code, 200)
        return [row['plate_number'] for row in response.data.get('overall_report', [])]

    def test_partial_left_digits_match_as_typed(self):
        self.assertCountEqual(self._plates(plate_left='1'), ['12 ب 345 67', '12 س 999 10'])
        self.assertCountEqual(self._plates(plate_left='12'), ['12 ب 345 67', '12 س 999 10'])

    def test_partial_mid_and_letter_combine(self):
        self.assertCountEqual(self._plates(plate_mid='34'), ['12 ب 345 67', '98 ب 345 11'])
        self.assertEqual(self._plates(plate_left='12', plate_letter='ب'), ['12 ب 345 67'])

    def test_partial_right_startswith(self):
        self.assertEqual(self._plates(plate_right='6'), ['12 ب 345 67'])
        self.assertEqual(self._plates(plate_right='67'), ['12 ب 345 67'])

    def test_helper_empty_returns_empty_q(self):
        self.assertFalse(_reports_plate_match_q())
