from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from unittest.mock import patch

from apps.auth.models import CarWash
from apps.vehicles.models import VehicleEntry
from apps.vehicles.views import _plate_parts_from_ai


class PlatePartsFromAiTests(APITestCase):
    def test_compact_latin_raw_text(self):
        parts = _plate_parts_from_ai(raw_text='67b34512', persian_text='')
        self.assertEqual(parts['plate_left'], '12')
        self.assertEqual(parts['plate_letter'], 'ب')
        self.assertEqual(parts['plate_mid'], '345')
        self.assertEqual(parts['plate_right'], '67')
        self.assertEqual(parts['plate_number'], '12 ب 345 67')

    def test_compact_latin_for_d_letter(self):
        parts = _plate_parts_from_ai(raw_text='64d15721', persian_text='')
        self.assertEqual(parts['plate_left'], '21')
        self.assertEqual(parts['plate_letter'], 'د')
        self.assertEqual(parts['plate_mid'], '157')
        self.assertEqual(parts['plate_right'], '64')
        self.assertEqual(parts['plate_number'], '21 د 157 64')

    def test_persian_visual_order_text(self):
        parts = _plate_parts_from_ai(raw_text='67b34512', persian_text='۶۷ ب ۳۴۵ ۱۲')
        self.assertEqual(parts['plate_number'], '12 ب 345 67')


class VehiclePlateRecognitionResponseTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.tenant = CarWash.objects.create(name='AI Wash', slug=f'ai-wash-{id(self)}')
        self.operator = user_model.objects.create_user(
            username=f'ai-operator-{id(self)}',
            password='pass12345',
            phone=f'0913{id(self) % 10000000:07d}',
            role='operator',
            tenant=self.tenant,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.operator)

    @patch('apps.vehicles.views.urlopen')
    def test_recognition_marks_accepted_when_parts_parsed(self, urlopen_mock):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return (
                    b'{"text":"64d15721","persian_text":"\\u06f6\\u0664 \\u062f \\u06f1\\u0665\\u0667 \\u06f2\\u0661",'
                    b'"confidence":0.91,"accepted":false}'
                )

        urlopen_mock.return_value = FakeResponse()
        response = self.client.post(
            reverse('vehicle-plate-recognition'),
            {'image_base64': 'data:image/jpeg;base64,ZmFrZQ==', 'force_process': True},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['accepted'])
        self.assertTrue(response.data['recognized'])
        self.assertEqual(response.data['plate_number'], '21 د 157 64')


class VehiclePlateLookupAutofillTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.tenant = CarWash.objects.create(name='Lookup Wash', slug=f'lookup-wash-{id(self)}')
        self.operator = user_model.objects.create_user(
            username=f'lookup-operator-{id(self)}',
            password='pass12345',
            phone=f'0914{id(self) % 10000000:07d}',
            role='operator',
            tenant=self.tenant,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.operator)
        VehicleEntry.objects.create(
            tenant=self.tenant,
            plate_number='21 د 157 64',
            plate_left='21',
            plate_letter='د',
            plate_mid='157',
            plate_right='64',
            plate_type=VehicleEntry.PlateType.CAR,
            car_model='پیکانتو',
            car_color='سفید',
            driver_name='میر حسینی',
            driver_phone='09125556677',
            status=VehicleEntry.Status.RELEASED,
        )

    def test_lookup_finds_vehicle_by_parts(self):
        response = self.client.get(
            reverse('vehicle-plate-lookup'),
            {
                'plate_left': '21',
                'plate_letter': 'د',
                'plate_mid': '157',
                'plate_right': '64',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['found'])
        self.assertEqual(response.data['car_model'], 'پیکانتو')
        self.assertEqual(response.data['driver_name'], 'میر حسینی')

    def test_lookup_finds_vehicle_with_alef_letter(self):
        VehicleEntry.objects.create(
            tenant=self.tenant,
            plate_number='11 الف 111 11',
            plate_left='11',
            plate_letter='الف',
            plate_mid='111',
            plate_right='11',
            plate_type=VehicleEntry.PlateType.CAR,
            car_model='پراید',
            car_color='قرمز',
            driver_name='Test Alef',
            driver_phone='09120001111',
            status=VehicleEntry.Status.RELEASED,
        )
        response = self.client.get(
            reverse('vehicle-plate-lookup'),
            {
                'plate_left': '11',
                'plate_letter': 'الف',
                'plate_mid': '111',
                'plate_right': '11',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['found'])
        self.assertEqual(response.data['car_model'], 'پراید')
