from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from apps.auth.models import CarWash
from apps.vehicles.models import BlockedPlate, VehicleEntry


class BlockPlateKeepsVisitActiveTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.tenant = CarWash.objects.create(name='Block Wash', slug='block-plate')
        self.manager = user_model.objects.create_user(
            username='block-plate-manager',
            password='pass12345',
            phone='09121112233',
            role='manager',
            tenant=self.tenant,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.manager)

    def test_block_plate_does_not_cancel_current_visit(self):
        create_response = self.client.post(
            reverse('vehicle-list-create'),
            {
                'plate_number': '11 ب 222 33',
                'plate_left': '11',
                'plate_letter': 'ب',
                'plate_mid': '222',
                'plate_right': '33',
                'plate_type': VehicleEntry.PlateType.CAR,
                'car_model': 'Pride',
                'car_color': 'White',
                'driver_name': 'Blocked Driver',
                'driver_phone': '09123334455',
                'status': VehicleEntry.Status.ENTERED,
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, 201)
        vehicle_id = create_response.data['id']

        block_response = self.client.post(
            reverse('vehicle-block-plate', args=[vehicle_id]),
            {},
            format='json',
        )
        self.assertEqual(block_response.status_code, 200)
        self.assertTrue(block_response.data['is_blocked'])
        self.assertFalse(block_response.data['cancelled'])
        self.assertEqual(block_response.data['vehicle']['status'], VehicleEntry.Status.ENTERED)
        self.assertTrue(block_response.data['vehicle']['is_plate_blocked'])
        self.assertTrue(BlockedPlate.objects.filter(tenant=self.tenant, plate_number='11 ب 222 33').exists())

    def test_block_plate_stores_note(self):
        create_response = self.client.post(
            reverse('vehicle-list-create'),
            {
                'plate_number': '22 ب 333 44',
                'plate_left': '22',
                'plate_letter': 'ب',
                'plate_mid': '333',
                'plate_right': '44',
                'plate_type': VehicleEntry.PlateType.CAR,
                'car_model': 'Pride',
                'car_color': 'White',
                'driver_name': 'Blocked Driver',
                'driver_phone': '09123334456',
                'status': VehicleEntry.Status.ENTERED,
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, 201)
        vehicle_id = create_response.data['id']

        block_response = self.client.post(
            reverse('vehicle-block-plate', args=[vehicle_id]),
            {'note': 'مشتری بدحساب'},
            format='json',
        )
        self.assertEqual(block_response.status_code, 200)
        self.assertEqual(block_response.data['note'], 'مشتری بدحساب')
        blocked = BlockedPlate.objects.get(tenant=self.tenant, plate_number='22 ب 333 44')
        self.assertEqual(blocked.note, 'مشتری بدحساب')

        vehicle = VehicleEntry.objects.get(id=vehicle_id)
        self.assertEqual(vehicle.status, VehicleEntry.Status.ENTERED)
