from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.auth.models import CarWash, SupportTicket
from apps.auth.sample_tenant import (
    SAMPLE_MASKED_NAME,
    SAMPLE_MASKED_PHONE,
    SAMPLE_MONTHLY_SMS_ALERT_THRESHOLD,
    SAMPLE_SMS_ALERT_CODE,
    assert_sample_sms_capacity,
    assert_sample_vehicle_capacity,
    create_or_refresh_sample_carwash,
    maybe_raise_sample_monthly_sms_alert,
)
from apps.auth.views import HqCarWashListCreateView, HqOverviewView, HqTicketListView
from apps.notifications.models import NotificationLog
from apps.subscriptions.models import ServiceAlert
from apps.vehicles.models import CustomerProfile, VehicleEntry
from apps.vehicles.serializers import VehicleEntrySerializer


User = get_user_model()


class SampleTenantTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.source = CarWash.objects.create(
            name='کارواش میلان',
            slug='milan-source',
            address='اصفهان',
            is_active=True,
            exclude_from_hq_reports=True,
        )
        self.source_manager = User.objects.create_user(
            username='milan_mgr',
            password='x',
            phone='09131111111',
            full_name='مدیر میلان',
            role=User.Roles.MANAGER,
            tenant=self.source,
        )
        self.worker_user = User.objects.create_user(
            username='milan_worker',
            password='x',
            phone='09132222222',
            full_name='علی کارگر',
            role=User.Roles.WORKER,
            tenant=self.source,
        )
        from apps.workers.models import WorkerProfile

        self.worker = WorkerProfile.objects.create(
            user=self.worker_user,
            tenant=self.source,
            code='W1',
        )
        CustomerProfile.objects.create(
            tenant=self.source,
            phone='09133333333',
            full_name='مشتری واقعی',
        )
        VehicleEntry.objects.create(
            tenant=self.source,
            plate_number='12ب34567',
            car_model='پژو',
            car_color='سفید',
            driver_name='مشتری واقعی',
            driver_phone='09133333333',
            entered_by=self.source_manager,
        )
        self.hq = User.objects.create_user(
            username='hq_admin_sample',
            password='x',
            phone='09120000099',
            full_name='HQ',
            role=User.Roles.ADMIN,
            platform_role=User.PlatformRoles.HQ_ADMIN,
            is_staff=True,
        )

    def test_clone_masks_historical_pii_and_hides_from_hq_lists(self):
        sample, manager = create_or_refresh_sample_carwash(source=self.source, force=True)
        self.assertTrue(sample.is_sample)
        self.assertEqual(manager.username, 'carnowash')
        self.assertTrue(manager.check_password('carnowash@123'))

        vehicles = list(VehicleEntry.objects.filter(tenant=sample))
        self.assertTrue(vehicles)
        self.assertTrue(all(v.driver_phone == SAMPLE_MASKED_PHONE for v in vehicles))
        self.assertTrue(all(v.driver_name == SAMPLE_MASKED_NAME for v in vehicles))

        workers = User.objects.filter(tenant=sample, role=User.Roles.WORKER)
        self.assertTrue(workers.exists())
        self.assertTrue(all(u.phone == SAMPLE_MASKED_PHONE for u in workers))
        self.assertTrue(all(u.full_name == SAMPLE_MASKED_NAME for u in workers))

        request = self.factory.get('/api/auth/hq/carwashes/')
        force_authenticate(request, user=self.hq)
        response = HqCarWashListCreateView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        names = [row['name'] for row in response.data]
        self.assertNotIn(sample.name, names)

        SupportTicket.objects.create(
            tenant=sample,
            created_by=manager,
            subject='تیکت نمونه',
            message='سلام',
            status=SupportTicket.Status.OPEN,
        )
        request = self.factory.get('/api/auth/hq/tickets/')
        force_authenticate(request, user=self.hq)
        response = HqTicketListView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        subjects = [row['subject'] for row in response.data]
        self.assertIn('تیکت نمونه', subjects)

        request = self.factory.get('/api/auth/hq/overview/')
        force_authenticate(request, user=self.hq)
        response = HqOverviewView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        recent_names = [row['name'] for row in response.data.get('recent_carwashes', [])]
        self.assertNotIn(sample.name, recent_names)

    def test_new_customer_stays_real_on_sample_tenant(self):
        sample, manager = create_or_refresh_sample_carwash(source=self.source, force=True)
        manager = User.objects.select_related('tenant').get(pk=manager.pk)
        self.assertEqual(manager.tenant_id, sample.id)

        request = self.factory.post('/api/vehicles/')
        force_authenticate(request, user=manager)
        request.user = manager
        serializer = VehicleEntrySerializer(
            data={
                'plate_number': '99الف99999',
                'car_model': 'دنا',
                'car_color': 'مشکی',
                'driver_name': 'رضا جدید',
                'driver_phone': '09135554433',
                'status': VehicleEntry.Status.ENTERED,
            },
            context={'request': request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        vehicle = serializer.save()
        self.assertEqual(vehicle.tenant_id, sample.id)
        self.assertEqual(vehicle.driver_name, 'رضا جدید')
        self.assertEqual(vehicle.driver_phone, '09135554433')
        customer = CustomerProfile.objects.get(phone='09135554433')
        self.assertEqual(customer.full_name, 'رضا جدید')
        self.assertEqual(customer.tenant_id, sample.id)

        masked = CustomerProfile.objects.get(phone=SAMPLE_MASKED_PHONE)
        self.assertEqual(masked.full_name, SAMPLE_MASKED_NAME)

    def test_sample_daily_caps_and_monthly_alert(self):
        sample, _manager = create_or_refresh_sample_carwash(source=self.source, force=True)
        sample.sample_daily_vehicle_limit = 1
        sample.sample_daily_sms_limit = 1
        sample.save(update_fields=['sample_daily_vehicle_limit', 'sample_daily_sms_limit'])

        # One historical vehicle may already count for "today" if check_in is today.
        # Force capacity by creating enough SENT sms logs.
        NotificationLog.objects.create(
            tenant=sample,
            channel=NotificationLog.Channel.SMS,
            recipient=SAMPLE_MASKED_PHONE,
            status=NotificationLog.Status.SENT,
            sent_at=timezone.now(),
        )
        with self.assertRaises(ValueError):
            assert_sample_sms_capacity(sample, extra=1)

        NotificationLog.objects.bulk_create(
            [
                NotificationLog(
                    tenant=sample,
                    channel=NotificationLog.Channel.SMS,
                    recipient=SAMPLE_MASKED_PHONE,
                    status=NotificationLog.Status.SENT,
                    sent_at=timezone.now(),
                )
                for _ in range(SAMPLE_MONTHLY_SMS_ALERT_THRESHOLD)
            ]
        )
        alert = maybe_raise_sample_monthly_sms_alert()
        self.assertIsNotNone(alert)
        self.assertEqual(alert.code, SAMPLE_SMS_ALERT_CODE)
        self.assertTrue(
            ServiceAlert.objects.filter(code=SAMPLE_SMS_ALERT_CODE, is_resolved=False).exists()
        )

        # Vehicle cap: fill today's count to limit
        VehicleEntry.objects.filter(tenant=sample).delete()
        sample.sample_daily_vehicle_limit = 1
        sample.save(update_fields=['sample_daily_vehicle_limit'])
        VehicleEntry.objects.create(
            tenant=sample,
            plate_number='11ب11111',
            car_model='x',
            car_color='y',
            driver_name=SAMPLE_MASKED_NAME,
            driver_phone=SAMPLE_MASKED_PHONE,
            entered_by=_manager,
        )
        with self.assertRaises(ValueError):
            assert_sample_vehicle_capacity(sample)
