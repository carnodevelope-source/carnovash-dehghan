from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from apps.auth.models import CarWash, CarWashFeaturePurchase
from apps.workers.models import WorkerProfile


class MenuAccessApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.client = APIClient()
        self.tenant = CarWash.objects.create(name='کارواش تست', slug='test-carwash')
        self.manager = user_model.objects.create_user(
            username='manager_menu',
            password='pass12345',
            phone='09120001001',
            role='manager',
            tenant=self.tenant,
        )
        self.hq_admin = user_model.objects.create_user(
            username='hq_admin_menu',
            password='pass12345',
            phone='09120001002',
            role='admin',
            platform_role='hq_admin',
            is_staff=True,
            is_superuser=False,
        )

    def test_me_returns_free_attendance_access_for_five_or_fewer_workers(self):
        self.client.force_authenticate(self.manager)
        user_model = get_user_model()
        worker_user = user_model.objects.create_user(
            username='worker_menu_free',
            password='pass12345',
            phone='09120001999',
            role='worker',
            tenant=self.tenant,
        )
        WorkerProfile.objects.create(user=worker_user, tenant=self.tenant)

        response = self.client.get(reverse('me'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['menu_access']['attendance'], True)
        self.assertEqual(response.data['purchased_menu_access'], [])

    def test_me_blocks_attendance_without_purchase_when_worker_count_exceeds_limit(self):
        self.client.force_authenticate(self.manager)
        user_model = get_user_model()
        for index in range(6):
            worker_user = user_model.objects.create_user(
                username=f'worker_menu_{index}',
                password='pass12345',
                phone=f'0912100{index:04d}',
                role='worker',
                tenant=self.tenant,
            )
            WorkerProfile.objects.create(user=worker_user, tenant=self.tenant)

        response = self.client.get(reverse('me'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['menu_access']['attendance'], True)
        self.assertEqual(response.data['purchased_menu_access'], [])
        self.assertEqual(response.data['attendance_upgrade_required'], True)

        CarWashFeaturePurchase.objects.create(
            tenant=self.tenant,
            feature_key=CarWashFeaturePurchase.FeatureKey.ATTENDANCE,
            is_active=True,
        )

        response = self.client.get(reverse('me'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['menu_access']['attendance'], True)
        self.assertEqual(response.data['purchased_menu_access'], ['attendance'])

    def test_hq_patch_persists_purchased_menu_access(self):
        self.client.force_authenticate(self.hq_admin)

        response = self.client.patch(
            reverse('hq-carwash-update', args=[self.tenant.id]),
            {'purchased_menu_access': ['attendance']},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['menu_access']['attendance'], True)
        self.assertTrue(
            CarWashFeaturePurchase.objects.filter(
                tenant=self.tenant,
                feature_key=CarWashFeaturePurchase.FeatureKey.ATTENDANCE,
                is_active=True,
            ).exists()
        )
