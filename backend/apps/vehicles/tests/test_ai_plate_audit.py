import base64
import json
import shutil
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from apps.auth.models import CarWash
from apps.vehicles.models import VehicleEntry


class AiPlateAuditModelColorTests(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._test_media_root = tempfile.mkdtemp(prefix='ai-audit-media-')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._test_media_root, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        user_model = get_user_model()
        self.tenant = CarWash.objects.create(name='Audit Wash', slug=f'audit-wash-{id(self)}')
        self.operator = user_model.objects.create_user(
            username=f'audit-operator-{id(self)}',
            password='pass12345',
            phone=f'0912{id(self) % 10000000:07d}',
            role='operator',
            tenant=self.tenant,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.operator)
        self.media_root = Path(self._test_media_root) / str(id(self))
        self.media_root.mkdir(parents=True, exist_ok=True)

    def test_create_admission_always_logs_model_and_color(self):
        image_b64 = base64.b64encode(b'fake-jpeg-bytes').decode('ascii')
        with override_settings(MEDIA_ROOT=str(self.media_root)):
            response = self.client.post(
                reverse('vehicle-list-create'),
                {
                    'plate_number': '12 ب 345 67',
                    'plate_left': '12',
                    'plate_letter': 'ب',
                    'plate_mid': '345',
                    'plate_right': '67',
                    'plate_type': VehicleEntry.PlateType.CAR,
                    'car_model': 'پژو 206',
                    'car_color': 'سفید',
                    'driver_name': 'Test Driver',
                    'driver_phone': '09120001111',
                    'status': VehicleEntry.Status.ENTERED,
                    'ai_raw_text': '67b34512',
                    'ai_persian_text': '۶۷ ب ۳۴۵ ۱۲',
                    'ai_converted_plate': '12 ب 345 67',
                    'ai_image_base64': f'data:image/jpeg;base64,{image_b64}',
                },
                format='json',
            )
            self.assertEqual(response.status_code, 201)

            log_path = self.media_root / 'ai_plate_audit' / 'plate_recognition_audit.jsonl'
            self.assertTrue(log_path.exists())
            rows = [json.loads(line) for line in log_path.read_text(encoding='utf-8').splitlines() if line.strip()]
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row['car_model'], 'پژو 206')
            self.assertEqual(row['car_color'], 'سفید')
            self.assertEqual(row['final_plate'], '12 ب 345 67')
            self.assertTrue(row['image_path'])

            image_path = self.media_root / row['image_path']
            sidecar_path = image_path.with_suffix('.json')
            self.assertTrue(image_path.exists())
            self.assertTrue(sidecar_path.exists())
            sidecar = json.loads(sidecar_path.read_text(encoding='utf-8'))
            self.assertEqual(sidecar['car_model'], 'پژو 206')
            self.assertEqual(sidecar['car_color'], 'سفید')

    def test_create_without_ai_still_logs_model_and_color(self):
        with override_settings(MEDIA_ROOT=str(self.media_root)):
            response = self.client.post(
                reverse('vehicle-list-create'),
                {
                    'plate_number': '22 د 222 22',
                    'plate_left': '22',
                    'plate_letter': 'د',
                    'plate_mid': '222',
                    'plate_right': '22',
                    'plate_type': VehicleEntry.PlateType.CAR,
                    'car_model': 'سمند',
                    'car_color': 'مشکی',
                    'driver_name': 'Manual Driver',
                    'driver_phone': '09120002222',
                    'status': VehicleEntry.Status.ENTERED,
                },
                format='json',
            )
            self.assertEqual(response.status_code, 201)
            log_path = self.media_root / 'ai_plate_audit' / 'plate_recognition_audit.jsonl'
            self.assertTrue(log_path.exists())
            row = json.loads(log_path.read_text(encoding='utf-8').strip().splitlines()[-1])
            self.assertEqual(row['operation'], 'create')
            self.assertEqual(row['car_model'], 'سمند')
            self.assertEqual(row['car_color'], 'مشکی')
