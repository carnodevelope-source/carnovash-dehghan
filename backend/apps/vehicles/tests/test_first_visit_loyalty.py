from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from apps.auth.models import CarWash
from apps.vehicles.loyalty import preview_next_loyalty_state, sync_plate_loyalty
from apps.vehicles.models import PlateLoyaltyProfile, VehicleEntry


class FirstVisitLoyaltyTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.tenant = CarWash.objects.create(name='First Visit Wash', slug='first-visit-loyalty')
        self.manager = user_model.objects.create_user(
            username='first-visit-manager',
            password='pass12345',
            phone='09121112233',
            role='manager',
            tenant=self.tenant,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.manager)

    def test_preview_first_visit_is_one_and_half_star(self):
        preview = preview_next_loyalty_state(None, discount_percent_per_half_star=Decimal('1'))
        self.assertEqual(preview['visit_count'], 1)
        self.assertEqual(preview['score'], 0.5)
        self.assertEqual(preview['visit_score'], 0.5)

    def test_plate_lookup_unknown_plate_returns_first_visit_preview(self):
        response = self.client.get(
            reverse('vehicle-plate-lookup'),
            {
                'plate_number': '77 D 777 77',
                'plate_left': '77',
                'plate_letter': 'D',
                'plate_mid': '777',
                'plate_right': '77',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['found'])
        self.assertEqual(response.data['customer_loyalty_visit_count'], 1)
        self.assertEqual(float(response.data['customer_score']), 0.5)

    def test_create_first_visit_persists_one_visit_and_score(self):
        response = self.client.post(
            reverse('vehicle-list-create'),
            {
                'plate_number': '88 H 888 88',
                'plate_left': '88',
                'plate_letter': 'H',
                'plate_mid': '888',
                'plate_right': '88',
                'plate_type': VehicleEntry.PlateType.CAR,
                'car_model': 'Pride',
                'car_color': 'White',
                'driver_name': 'First Customer',
                'driver_phone': '09123334455',
                'status': VehicleEntry.Status.ENTERED,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['customer_loyalty_visit_count'], 1)
        self.assertEqual(float(response.data['customer_score']), 0.5)

        loyalty = PlateLoyaltyProfile.objects.get(tenant=self.tenant, plate_number=response.data['plate_number'])
        self.assertEqual(loyalty.visit_count, 1)
        self.assertEqual(loyalty.score, Decimal('0.5'))

    def test_sync_repairs_zero_visit_profile_with_existing_vehicle(self):
        vehicle = VehicleEntry.objects.create(
            tenant=self.tenant,
            plate_number='99 V 999 99',
            plate_left='99',
            plate_letter='V',
            plate_mid='999',
            plate_right='99',
            plate_type=VehicleEntry.PlateType.CAR,
            car_model='Samand',
            car_color='Black',
            driver_name='Repair Customer',
            driver_phone='09125556677',
            status=VehicleEntry.Status.ENTERED,
        )
        profile = PlateLoyaltyProfile.objects.create(
            tenant=self.tenant,
            plate_number=vehicle.plate_number,
            plate_left=vehicle.plate_left,
            plate_letter=vehicle.plate_letter,
            plate_mid=vehicle.plate_mid,
            plate_right=vehicle.plate_right,
            visit_count=0,
            cycle_visit_count=0,
            score=Decimal('0'),
        )

        synced = sync_plate_loyalty(profile, discount_percent_per_half_star=Decimal('1'))
        self.assertEqual(synced.visit_count, 1)
        self.assertEqual(synced.score, Decimal('0.5'))
