from unittest.mock import patch
from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.auth.models import CarWash
from apps.notifications.models import NotificationLog
from apps.payments.models import Wallet
from apps.services.models import GeneralSettings
from apps.vehicles.models import (
    CustomerProfile,
    PlateLoyaltyProfile,
    VehicleEntry,
    VehicleJob,
    VehicleJobService,
)


@override_settings(
    IRANPAYAMAK_API_KEY='test-api-key',
    IRANPAYAMAK_LINE_NUMBER='30001234',
    IRANPAYAMAK_BASE_URL='https://api.iranpayamak.com',
    SMS_PRICE_PER_SEGMENT=500,
)
class VehicleStatusSmsTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.tenant = CarWash.objects.create(name='کارواش تست', slug='vehicle-status-sms')
        self.manager = user_model.objects.create_user(
            username='vehicle-status-manager',
            password='pass12345',
            phone='09129991111',
            role='manager',
            tenant=self.tenant,
        )
        self.sms_wallet = Wallet.objects.create(
            tenant=self.tenant,
            name='کیف پول پیامک',
            wallet_type=Wallet.WalletType.SMS,
            balance=500000,
            is_active=True,
        )
        self.vehicle = VehicleEntry.objects.create(
            tenant=self.tenant,
            plate_number='22 ب 345 67',
            plate_left='22',
            plate_letter='ب',
            plate_mid='345',
            plate_right='67',
            plate_type=VehicleEntry.PlateType.CAR,
            car_model='207',
            car_color='سفید',
            driver_name='علی رضایی',
            driver_phone='09120000000',
            status=VehicleEntry.Status.ENTERED,
            entered_by=self.manager,
            updated_by=self.manager,
        )
        self.job = VehicleJob.objects.create(
            tenant=self.tenant,
            vehicle=self.vehicle,
            services_total=1200000,
            final_total=1200000,
            discount_total=100000,
            manual_discount_total=50000,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.manager)

    @patch('apps.notifications.services.send_provider_sms')
    def test_status_update_sends_assignment_sms_when_marked_ready(self, mock_send_provider_sms):
        mock_send_provider_sms.return_value = {
            'ok': True,
            'message': 'پیامک با موفقیت در صف ارسال قرار گرفت.',
            'provider_status': 200,
            'provider_data': {'status': 'success', 'data': {'id': 'provider-1'}},
            'provider_id': 'provider-1',
            'raw_body': '{"status":"success","data":{"id":"provider-1"}}',
            'payload': {'line_number': '30001234', 'recipients': ['09120000000']},
        }

        response = self.client.patch(
            reverse('vehicle-status-update', args=[self.vehicle.id]),
            {'status': VehicleEntry.Status.READY_TO_SETTLE},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.vehicle.refresh_from_db()
        self.sms_wallet.refresh_from_db()
        self.assertEqual(self.vehicle.status, VehicleEntry.Status.READY_TO_SETTLE)
        self.assertTrue(
            NotificationLog.objects.filter(
                tenant=self.tenant,
                vehicle_entry=self.vehicle,
                template_code='vehicle_assigned',
                status=NotificationLog.Status.SENT,
                recipient='09120000000',
            ).exists()
        )
        self.assertLess(int(self.sms_wallet.balance), 500000)
        log = NotificationLog.objects.get(
            tenant=self.tenant,
            vehicle_entry=self.vehicle,
            template_code='vehicle_assigned',
            status=NotificationLog.Status.SENT,
        )
        self.assertEqual(log.provider_response, '{"status":"success","data":{"id":"provider-1"}}')
        self.assertEqual(log.payload['provider_request']['line_number'], '30001234')

    def test_admission_number_starts_from_1000_and_increments_daily(self):
        self.assertEqual(self.vehicle.admission_number, 1000)

        second_vehicle = VehicleEntry.objects.create(
            tenant=self.tenant,
            plate_number='33 ج 444 55',
            plate_left='33',
            plate_letter='ج',
            plate_mid='444',
            plate_right='55',
            plate_type=VehicleEntry.PlateType.CAR,
            car_model='دنا',
            car_color='مشکی',
            driver_name='مشتری تست',
            driver_phone='09121112222',
            status=VehicleEntry.Status.ENTERED,
            entered_by=self.manager,
            updated_by=self.manager,
        )

        self.assertEqual(second_vehicle.admission_number, 1001)

    def test_vehicle_list_filters_by_check_in_date_range(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        yesterday_start = timezone.make_aware(
            datetime.combine(yesterday, datetime.min.time()),
            timezone.get_current_timezone(),
        )
        old_vehicle = VehicleEntry.objects.create(
            tenant=self.tenant,
            plate_number='44 د 555 66',
            plate_left='44',
            plate_letter='د',
            plate_mid='555',
            plate_right='66',
            plate_type=VehicleEntry.PlateType.CAR,
            car_model='سمند',
            car_color='نقره‌ای',
            driver_name='مشتری دیروز',
            driver_phone='09123334444',
            status=VehicleEntry.Status.ENTERED,
            entered_by=self.manager,
            updated_by=self.manager,
        )
        VehicleEntry.objects.filter(pk=old_vehicle.pk).update(check_in_at=yesterday_start)

        today = timezone.localdate().isoformat()
        response = self.client.get(reverse('vehicle-list-create'), {'date_start': today, 'date_end': today})

        self.assertEqual(response.status_code, 200)
        returned_ids = {item['id'] for item in response.data}
        self.assertIn(self.vehicle.id, returned_ids)
        self.assertNotIn(old_vehicle.id, returned_ids)

    @patch('apps.notifications.services.send_provider_sms')
    def test_status_update_sends_release_sms_when_marked_released(self, mock_send_provider_sms):
        mock_send_provider_sms.return_value = {
            'ok': True,
            'message': 'پیامک با موفقیت در صف ارسال قرار گرفت.',
            'provider_status': 200,
            'provider_data': {'status': 'success', 'data': {'id': 'provider-2'}},
            'provider_id': 'provider-2',
            'raw_body': '{"status":"success","data":{"id":"provider-2"}}',
            'payload': {'line_number': '30001234', 'recipients': ['09120000000']},
        }
        self.vehicle.status = VehicleEntry.Status.READY_TO_SETTLE
        self.vehicle.save(update_fields=['status', 'updated_at'])

        response = self.client.patch(
            reverse('vehicle-status-update', args=[self.vehicle.id]),
            {'status': VehicleEntry.Status.RELEASED},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.vehicle.refresh_from_db()
        self.sms_wallet.refresh_from_db()
        self.assertEqual(self.vehicle.status, VehicleEntry.Status.RELEASED)
        self.assertTrue(
            NotificationLog.objects.filter(
                tenant=self.tenant,
                vehicle_entry=self.vehicle,
                template_code='vehicle_released',
                status=NotificationLog.Status.SENT,
                recipient='09120000000',
            ).exists()
        )
        self.assertLess(int(self.sms_wallet.balance), 500000)

    @patch('apps.notifications.services.send_provider_sms')
    def test_assignment_modal_create_path_sends_assignment_sms(self, mock_send_provider_sms):
        mock_send_provider_sms.return_value = {
            'ok': True,
            'message': 'پیامک با موفقیت در صف ارسال قرار گرفت.',
            'provider_status': 200,
            'provider_data': {'status': 'success', 'data': {'id': 'provider-3'}},
            'provider_id': 'provider-3',
            'raw_body': '{"status":"success","data":{"id":"provider-3"}}',
            'payload': {'line_number': '30001234', 'recipients': ['09121112222']},
        }

        response = self.client.post(
            reverse('vehicle-list-create'),
            {
                'plate_number': '33 ج 444 55',
                'plate_left': '33',
                'plate_letter': 'ج',
                'plate_mid': '444',
                'plate_right': '55',
                'plate_type': VehicleEntry.PlateType.CAR,
                'car_model': 'دنا',
                'car_color': 'مشکی',
                'driver_name': 'مشتری تست',
                'driver_phone': '09121112222',
                'status': VehicleEntry.Status.READY_TO_SETTLE,
                'services': [{'title': 'شست‌وشو', 'price': 500000}],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        vehicle = VehicleEntry.objects.get(id=response.data['id'])
        self.assertTrue(
            NotificationLog.objects.filter(
                tenant=self.tenant,
                vehicle_entry=vehicle,
                template_code='vehicle_assigned',
                status=NotificationLog.Status.SENT,
                recipient='09121112222',
            ).exists()
        )
        log = NotificationLog.objects.get(
            tenant=self.tenant,
            vehicle_entry=vehicle,
            template_code='vehicle_assigned',
            status=NotificationLog.Status.SENT,
        )
        self.assertIn('شست‌وشو', log.payload.get('text', ''))
        self.assertIn('۵۰۰', log.payload.get('text', ''))

    @patch('apps.notifications.services.send_provider_sms')
    def test_assignment_modal_can_disable_assignment_and_release_sms_for_vehicle(self, mock_send_provider_sms):
        mock_send_provider_sms.return_value = {
            'ok': True,
            'message': 'پیامک با موفقیت در صف ارسال قرار گرفت.',
            'provider_status': 200,
            'provider_data': {'status': 'success', 'data': {'id': 'provider-disabled'}},
            'provider_id': 'provider-disabled',
            'raw_body': '{"status":"success","data":{"id":"provider-disabled"}}',
            'payload': {'line_number': '30001234', 'recipients': ['09121113333']},
        }

        create_response = self.client.post(
            reverse('vehicle-list-create'),
            {
                'plate_number': '33 ج 444 56',
                'plate_left': '33',
                'plate_letter': 'ج',
                'plate_mid': '444',
                'plate_right': '56',
                'plate_type': VehicleEntry.PlateType.CAR,
                'car_model': 'دنا',
                'car_color': 'مشکی',
                'driver_name': 'مشتری بدون پیامک',
                'driver_phone': '09121113333',
                'status': VehicleEntry.Status.READY_TO_SETTLE,
                'sms_notifications_enabled': False,
                'services': [{'title': 'شست‌وشو', 'price': 500000}],
            },
            format='json',
        )

        self.assertEqual(create_response.status_code, 201)
        vehicle = VehicleEntry.objects.get(id=create_response.data['id'])
        self.assertFalse(vehicle.sms_notifications_enabled)
        self.assertFalse(
            NotificationLog.objects.filter(
                tenant=self.tenant,
                vehicle_entry=vehicle,
                template_code='vehicle_assigned',
            ).exists()
        )

        release_response = self.client.patch(
            reverse('vehicle-release-checkout', args=[vehicle.id]),
            {'payment_method': 'cash'},
            format='json',
        )

        self.assertEqual(release_response.status_code, 200)
        self.assertFalse(
            NotificationLog.objects.filter(
                tenant=self.tenant,
                vehicle_entry=vehicle,
                template_code='vehicle_released',
            ).exists()
        )
        mock_send_provider_sms.assert_not_called()

    @patch('apps.notifications.services.send_provider_sms')
    def test_general_settings_can_disable_automatic_assignment_sms(self, mock_send_provider_sms):
        GeneralSettings.objects.create(
            tenant=self.tenant,
            sms_vehicle_auto_send_enabled=False,
        )

        response = self.client.patch(
            reverse('vehicle-status-update', args=[self.vehicle.id]),
            {'status': VehicleEntry.Status.READY_TO_SETTLE},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            NotificationLog.objects.filter(
                tenant=self.tenant,
                vehicle_entry=self.vehicle,
                template_code='vehicle_assigned',
            ).exists()
        )
        mock_send_provider_sms.assert_not_called()

    @patch('apps.notifications.services.send_provider_sms')
    def test_general_settings_can_disable_automatic_release_sms(self, mock_send_provider_sms):
        GeneralSettings.objects.create(
            tenant=self.tenant,
            sms_vehicle_auto_send_enabled=False,
        )
        self.vehicle.status = VehicleEntry.Status.READY_TO_SETTLE
        self.vehicle.save(update_fields=['status', 'updated_at'])

        response = self.client.patch(
            reverse('vehicle-release-checkout', args=[self.vehicle.id]),
            {'payment_method': 'cash', 'sms_notifications_enabled': True},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            NotificationLog.objects.filter(
                tenant=self.tenant,
                vehicle_entry=self.vehicle,
                template_code='vehicle_released',
            ).exists()
        )
        mock_send_provider_sms.assert_not_called()

    @patch('apps.notifications.services.send_provider_sms')
    def test_assignment_sms_uses_persisted_service_lines_and_non_zero_total(self, mock_send_provider_sms):
        mock_send_provider_sms.return_value = {
            'ok': True,
            'message': 'پیامک با موفقیت در صف ارسال قرار گرفت.',
            'provider_status': 200,
            'provider_data': {'status': 'success', 'data': {'id': 'provider-3b'}},
            'provider_id': 'provider-3b',
            'raw_body': '{"status":"success","data":{"id":"provider-3b"}}',
            'payload': {'line_number': '30001234', 'recipients': ['09120000000']},
        }
        VehicleJobService.objects.create(
            tenant=self.tenant,
            vehicle_job=self.job,
            custom_service_name='تمیزکاری',
            quantity=1,
            unit_price=500000,
            line_total=500000,
            is_completed=True,
        )
        self.job.services_total = 500000
        self.job.final_total = 0
        self.job.save(update_fields=['services_total', 'final_total', 'updated_at'])

        response = self.client.patch(
            reverse('vehicle-status-update', args=[self.vehicle.id]),
            {'status': VehicleEntry.Status.READY_TO_SETTLE},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        log = NotificationLog.objects.get(
            tenant=self.tenant,
            vehicle_entry=self.vehicle,
            template_code='vehicle_assigned',
            status=NotificationLog.Status.SENT,
        )
        self.assertIn('تمیزکاری', log.payload.get('text', ''))
        self.assertIn('۵۰۰', log.payload.get('text', ''))
        self.assertNotIn('جمع کل: ۰ تومان', log.payload.get('text', ''))

    @patch('apps.notifications.services.send_provider_sms')
    def test_release_modal_endpoint_sends_release_sms(self, mock_send_provider_sms):
        mock_send_provider_sms.return_value = {
            'ok': True,
            'message': 'پیامک با موفقیت در صف ارسال قرار گرفت.',
            'provider_status': 200,
            'provider_data': {'status': 'success', 'data': {'id': 'provider-4'}},
            'provider_id': 'provider-4',
            'raw_body': '{"status":"success","data":{"id":"provider-4"}}',
            'payload': {'line_number': '30001234', 'recipients': ['09120000000']},
        }
        self.vehicle.status = VehicleEntry.Status.READY_TO_SETTLE
        self.vehicle.save(update_fields=['status', 'updated_at'])

        response = self.client.patch(
            reverse('vehicle-release-checkout', args=[self.vehicle.id]),
            {'payment_method': 'cash'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, VehicleEntry.Status.RELEASED)
        self.assertTrue(
            NotificationLog.objects.filter(
                tenant=self.tenant,
                vehicle_entry=self.vehicle,
                template_code='vehicle_released',
                status=NotificationLog.Status.SENT,
                recipient='09120000000',
                provider_message_id='provider-4',
            ).exists()
        )

    @patch('apps.notifications.services.send_provider_sms')
    def test_release_checkout_counts_facility_discount_once_from_list_price(self, mock_send_provider_sms):
        mock_send_provider_sms.return_value = {
            'ok': True,
            'message': 'sent',
            'provider_status': 200,
            'provider_data': {'status': 'success', 'data': {'id': 'provider-discount'}} ,
            'provider_id': 'provider-discount',
            'raw_body': '{"status":"success","data":{"id":"provider-discount"}}',
            'payload': {'line_number': '30001234', 'recipients': ['09120000000']},
        }
        GeneralSettings.objects.create(
            tenant=self.tenant,
            discount_percent_per_half_star=Decimal('0.5'),
            tax_enabled=False,
        )
        PlateLoyaltyProfile.objects.create(
            tenant=self.tenant,
            plate_number=self.vehicle.plate_number,
            plate_left=self.vehicle.plate_left,
            plate_letter=self.vehicle.plate_letter,
            plate_mid=self.vehicle.plate_mid,
            plate_right=self.vehicle.plate_right,
            score=Decimal('4.0'),
            next_discount_percent=Decimal('4.00'),
            visit_count=8,
        )
        self.job.manual_discount_total = Decimal('20000')
        self.job.save(update_fields=['manual_discount_total', 'updated_at'])
        VehicleJobService.objects.create(
            tenant=self.tenant,
            vehicle_job=self.job,
            custom_service_name='discounted service',
            quantity=1,
            list_unit_price=Decimal('450000'),
            unit_price=Decimal('400000'),
            line_total=Decimal('400000'),
            discount_amount=Decimal('50000'),
            is_completed=True,
        )
        self.vehicle.status = VehicleEntry.Status.READY_TO_SETTLE
        self.vehicle.save(update_fields=['status', 'updated_at'])

        response = self.client.patch(
            reverse('vehicle-release-checkout', args=[self.vehicle.id]),
            {'payment_method': 'cash'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.job.refresh_from_db()
        self.assertEqual(self.job.service_list_subtotal, Decimal('450000.00'))
        self.assertEqual(self.job.services_total, Decimal('400000.00'))
        self.assertEqual(self.job.facility_discount_total, Decimal('50000.00'))
        self.assertEqual(self.job.loyalty_discount_total, Decimal('18000.00'))
        self.assertEqual(self.job.manual_discount_total, Decimal('20000.00'))
        self.assertEqual(self.job.discount_total, Decimal('88000.00'))
        self.assertEqual(self.job.final_total, Decimal('362000.00'))
        log = NotificationLog.objects.get(
            tenant=self.tenant,
            vehicle_entry=self.vehicle,
            template_code='vehicle_released',
            status=NotificationLog.Status.SENT,
        )
        self.assertEqual(log.payload['final_total'], 362000.0)
        self.assertEqual(log.payload['discount_total'], 88000.0)
        self.assertEqual(log.payload['facility_discount_total'], 50000.0)
        self.assertEqual(log.payload['loyalty_discount_total'], 18000.0)
        self.assertEqual(log.payload['manual_discount_total'], 20000.0)

    @patch('apps.notifications.services.send_provider_sms')
    def test_vehicle_create_reuses_existing_customer_profile_by_phone(self, mock_send_provider_sms):
        mock_send_provider_sms.return_value = {
            'ok': True,
            'message': 'پیامک با موفقیت در صف ارسال قرار گرفت.',
            'provider_status': 200,
            'provider_data': {'status': 'success', 'data': {'id': 'provider-5'}},
            'provider_id': 'provider-5',
            'raw_body': '{"status":"success","data":{"id":"provider-5"}}',
            'payload': {'line_number': '30001234', 'recipients': ['09123334444']},
        }
        existing_customer = CustomerProfile.objects.create(
            tenant=self.tenant,
            phone='09123334444',
            full_name='مشتری قدیمی',
        )

        response = self.client.post(
            reverse('vehicle-list-create'),
            {
                'plate_number': '44 د 555 66',
                'plate_left': '44',
                'plate_letter': 'د',
                'plate_mid': '555',
                'plate_right': '66',
                'plate_type': VehicleEntry.PlateType.CAR,
                'car_model': 'تارا',
                'car_color': 'نقره ای',
                'driver_name': 'مشتری جدید',
                'driver_phone': '09123334444',
                'status': VehicleEntry.Status.READY_TO_SETTLE,
                'services': [{'title': 'واکس', 'price': 350000}],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        vehicle = VehicleEntry.objects.get(id=response.data['id'])
        self.assertEqual(vehicle.customer_id, existing_customer.id)
        existing_customer.refresh_from_db()
        self.assertEqual(existing_customer.full_name, 'مشتری جدید')
