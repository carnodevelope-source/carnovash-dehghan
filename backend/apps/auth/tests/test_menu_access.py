from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from apps.auth.models import CarWash, CarWashFeaturePurchase


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

    def test_me_returns_dynamic_menu_access_from_purchases(self):
        self.client.force_authenticate(self.manager)

        response = self.client.get(reverse('me'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['menu_access']['attendance'], False)
        self.assertEqual(response.data['purchased_menu_access'], [])

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
