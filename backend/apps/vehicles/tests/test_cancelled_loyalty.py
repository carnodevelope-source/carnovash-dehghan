from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from apps.auth.models import CarWash
from apps.vehicles.models import CustomerProfile, PlateLoyaltyProfile, VehicleEntry


class CancelledVehicleLoyaltyTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.tenant = CarWash.objects.create(name='Test Wash', slug='cancelled-loyalty')
        self.manager = user_model.objects.create_user(
            username='cancelled-loyalty-manager',
            password='pass12345',
            phone='09129992222',
            role='manager',
            tenant=self.tenant,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.manager)

    def test_cancelled_vehicle_is_removed_from_loyalty_visit_count(self):
        response = self.client.post(
            reverse('vehicle-list-create'),
            {
                'plate_number': '55 B 123 44',
                'plate_left': '55',
                'plate_letter': 'B',
                'plate_mid': '123',
                'plate_right': '44',
                'plate_type': VehicleEntry.PlateType.CAR,
                'car_model': 'Test',
                'car_color': 'White',
                'driver_name': 'Cancel Customer',
                'driver_phone': '09124445555',
                'status': VehicleEntry.Status.ENTERED,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        vehicle = VehicleEntry.objects.get(id=response.data['id'])
        loyalty = PlateLoyaltyProfile.objects.get(tenant=self.tenant, plate_number=vehicle.plate_number)
        customer = CustomerProfile.objects.get(phone='09124445555')
        self.assertEqual(loyalty.visit_count, 1)
        self.assertEqual(customer.yearly_score, Decimal('0.5'))

        cancel_response = self.client.patch(
            reverse('vehicle-status-update', args=[vehicle.id]),
            {'status': VehicleEntry.Status.CANCELLED},
            format='json',
        )

        self.assertEqual(cancel_response.status_code, 200)
        loyalty.refresh_from_db()
        customer.refresh_from_db()
        self.assertEqual(loyalty.visit_count, 0)
        self.assertEqual(loyalty.cycle_visit_count, 0)
        self.assertEqual(loyalty.score, Decimal('0.0'))
        self.assertEqual(customer.yearly_score, Decimal('0.0'))

