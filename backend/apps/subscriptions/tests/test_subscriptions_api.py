from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from apps.auth.models import CarWash, CarWashFeaturePurchase, User
from apps.payments.models import Wallet
from apps.subscriptions.models import ServiceOrder, ServicePeriod, ServiceProduct, ServiceSubscription
from apps.subscriptions.services import (
    apply_hq_action,
    create_order_and_activate,
    renew_subscription,
    seed_catalog_from_legacy,
    summarize_subscriptions,
)


class SubscriptionsApiTests(APITestCase):
    def setUp(self):
        self.tenant = CarWash.objects.create(name='کارواش تست سرویس', slug='svc-test', is_active=True)
        self.hq_admin = User.objects.create_user(
            username='hq_admin_svc',
            email='hq_admin_svc@example.com',
            phone='09120000011',
            password='Pass1234!',
            platform_role=User.PlatformRoles.HQ_ADMIN,
        )
        self.hq_support = User.objects.create_user(
            username='hq_support_svc',
            email='hq_support_svc@example.com',
            phone='09120000012',
            password='Pass1234!',
            platform_role=User.PlatformRoles.HQ_SUPPORT,
        )
        self.manager = User.objects.create_user(
            username='manager_svc',
            email='manager_svc@example.com',
            phone='09120000013',
            password='Pass1234!',
            role=User.Roles.MANAGER,
            tenant=self.tenant,
        )
        Wallet.objects.create(
            tenant=self.tenant,
            name='کیف پول اصلی',
            wallet_type=Wallet.WalletType.BANK,
            balance=Decimal('50000000'),
            is_active=True,
        )
        self.project = seed_catalog_from_legacy()
        self.product = ServiceProduct.objects.get(project=self.project, product_key='attendance')
        self.plan = self.product.plans.filter(is_active=True).first()

    def test_hq_summary_and_list(self):
        create_order_and_activate(
            tenant=self.tenant,
            product=self.product,
            plan=self.plan,
            actor=self.hq_admin,
            payment_method=ServiceOrder.PaymentMethod.MANUAL_HQ,
        )
        self.client.force_authenticate(self.hq_admin)
        summary = self.client.get('/api/subscriptions/hq/summary/')
        self.assertEqual(summary.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(summary.data['active_count'], 1)
        listing = self.client.get('/api/subscriptions/hq/subscriptions/')
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(listing.data['count'], 1)

    def test_support_cannot_see_profit_and_cannot_mutate(self):
        order = create_order_and_activate(
            tenant=self.tenant,
            product=self.product,
            plan=self.plan,
            actor=self.hq_admin,
            payment_method=ServiceOrder.PaymentMethod.MANUAL_HQ,
        )
        self.client.force_authenticate(self.hq_support)
        summary = self.client.get('/api/subscriptions/hq/summary/')
        self.assertEqual(summary.status_code, status.HTTP_200_OK)
        self.assertNotIn('carno_paid', summary.data)
        self.assertNotIn('arakar_paid', summary.data)
        action = self.client.post(
            f'/api/subscriptions/hq/subscriptions/{order.subscription_id}/actions/',
            {'action': 'block', 'reason': 'test'},
            format='json',
        )
        self.assertEqual(action.status_code, status.HTTP_403_FORBIDDEN)

    def test_renew_keeps_period_history(self):
        order = create_order_and_activate(
            tenant=self.tenant,
            product=self.product,
            plan=self.plan,
            actor=self.hq_admin,
            payment_method=ServiceOrder.PaymentMethod.MANUAL_HQ,
        )
        sub = order.subscription
        renew_subscription(sub, actor=self.hq_admin, payment_method=ServiceOrder.PaymentMethod.MANUAL_HQ)
        self.assertGreaterEqual(ServicePeriod.objects.filter(subscription=sub).count(), 2)

    def test_hq_action_block_and_audit(self):
        order = create_order_and_activate(
            tenant=self.tenant,
            product=self.product,
            plan=self.plan,
            actor=self.hq_admin,
            payment_method=ServiceOrder.PaymentMethod.MANUAL_HQ,
        )
        sub = apply_hq_action(order.subscription, action='block', actor=self.hq_admin, reason='بدهی')
        self.assertEqual(sub.status, ServiceSubscription.Status.BLOCKED)
        self.assertTrue(sub.audit_logs.filter(action='block').exists())

    def test_export_requires_capability(self):
        self.client.force_authenticate(self.hq_support)
        response = self.client.get('/api/subscriptions/hq/export/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(self.hq_admin)
        response = self.client.get('/api/subscriptions/hq/export/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('text/csv', response['Content-Type'])

    def test_client_services_shows_missing_products(self):
        self.client.force_authenticate(self.hq_admin)
        response = self.client.get(f'/api/subscriptions/hq/clients/{self.tenant.id}/services/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('not_purchased', response.data)
        self.assertTrue(len(response.data['not_purchased']) > 0)

    def test_wallet_purchase_syncs_subscription(self):
        self.client.force_authenticate(self.manager)
        feature_key = CarWashFeaturePurchase.FeatureKey.ATTENDANCE
        response = self.client.post(
            '/api/payments/wallet/options/',
            {'feature_key': feature_key, 'payment_plan': 'cash'},
            format='json',
        )
        self.assertIn(response.status_code, {status.HTTP_200_OK, status.HTTP_201_CREATED})
        self.assertTrue(
            ServiceSubscription.objects.filter(
                tenant=self.tenant,
                product__feature_key=feature_key,
            ).exists()
        )

    def test_tenant_forbidden_from_hq_endpoints(self):
        self.client.force_authenticate(self.manager)
        response = self.client.get('/api/subscriptions/hq/summary/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_summarize_helper(self):
        create_order_and_activate(
            tenant=self.tenant,
            product=self.product,
            plan=self.plan,
            actor=self.hq_admin,
            payment_method=ServiceOrder.PaymentMethod.MANUAL_HQ,
        )
        data = summarize_subscriptions()
        self.assertIn('active_count', data)
        self.assertGreaterEqual(data['active_count'], 1)
