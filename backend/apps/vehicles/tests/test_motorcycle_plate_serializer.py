from django.test import SimpleTestCase

from apps.vehicles.serializers import VehicleEntrySerializer


class MotorcyclePlateSerializerTests(SimpleTestCase):
    def test_ai_confidence_rounds_long_precision_without_validation_error(self):
        serializer = VehicleEntrySerializer(data={
            'plate_type': 'car',
            'plate_number': '57 ر 956 12',
            'plate_left': '57',
            'plate_letter': 'ر',
            'plate_mid': '956',
            'plate_right': '12',
            'ai_confidence': '0.956120121',
            'driver_name': 'Test Driver',
            'driver_phone': '',
            'status': 'entered',
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['ai_confidence'].as_tuple().exponent, -2)
        self.assertEqual(str(serializer.validated_data['ai_confidence']), '0.96')

    def test_car_plate_trims_ai_overflow_without_validation_error(self):
        serializer = VehicleEntrySerializer(data={
            'plate_type': 'car',
            'plate_number': '22 ب 345 67',
            'plate_left': '22',
            'plate_letter': 'ب',
            'plate_mid': '345',
            'plate_right': '67',
            'ai_converted_plate_left': '229',
            'ai_converted_plate_letter': 'بببببب',
            'ai_converted_plate_mid': '3459',
            'ai_converted_plate_right': '679',
            'driver_name': 'Test Driver',
            'driver_phone': '',
            'status': 'entered',
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['plate_left'], '22')
        self.assertEqual(serializer.validated_data['plate_letter'], 'ب')
        self.assertEqual(serializer.validated_data['plate_mid'], '345')
        self.assertEqual(serializer.validated_data['plate_right'], '67')

    def test_car_plate_uses_letter_as_letter_not_digit_bucket(self):
        serializer = VehicleEntrySerializer(data={
            'plate_type': 'car',
            'plate_number': '22 ب 345 67',
            'plate_left': '229',
            'plate_letter': '222ب34567',
            'plate_mid': '3459',
            'plate_right': '679',
            'driver_name': 'Test Driver',
            'driver_phone': '',
            'status': 'entered',
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['plate_left'], '22')
        self.assertEqual(serializer.validated_data['plate_letter'], 'ب')
        self.assertEqual(serializer.validated_data['plate_mid'], '345')
        self.assertEqual(serializer.validated_data['plate_right'], '67')

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

    def test_motorcycle_plate_trims_ocr_overflow_without_validation_error(self):
        serializer = VehicleEntrySerializer(data={
            'plate_type': 'motorcycle',
            'plate_number': '222 333339',
            'plate_mid': '2229',
            'plate_letter': '333339',
            'ai_converted_plate_mid': '2229',
            'ai_converted_plate_letter': '333339',
            'driver_name': 'Test Rider',
            'driver_phone': '',
            'status': 'entered',
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['plate_mid'], '222')
        self.assertEqual(serializer.validated_data['plate_letter'], '33333')
        self.assertEqual(serializer.validated_data['plate_number'], '222 33333')
