from django.test import SimpleTestCase

from apps.vehicles.serializers import VehicleEntrySerializer


class MotorcyclePlateSerializerTests(SimpleTestCase):
    def test_motorcycle_plate_ignores_car_side_fields(self):
        serializer = VehicleEntrySerializer(data={
            'plate_type': 'motorcycle',
            'plate_number': 'IRAN 222 33333',
            'plate_left': 'IRAN',
            'plate_mid': '222',
            'plate_letter': '33333',
            'plate_right': 'IRAN',
            'driver_name': 'Test Rider',
            'driver_phone': '',
            'status': 'entered',
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['plate_left'], '')
        self.assertEqual(serializer.validated_data['plate_right'], '')
        self.assertEqual(serializer.validated_data['plate_mid'], '222')
        self.assertEqual(serializer.validated_data['plate_letter'], '33333')
        self.assertEqual(serializer.validated_data['plate_number'], '222 33333')
