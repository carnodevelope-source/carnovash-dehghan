from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.auth.models import CarWash
from apps.payments.models import Payment
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

    def test_released_vehicle_cancellation_is_removed_from_reports_and_loyalty(self):
        response = self.client.post(
            reverse('vehicle-list-create'),
            {
                'plate_number': '66 C 321 55',
                'plate_left': '66',
                'plate_letter': 'C',
                'plate_mid': '321',
                'plate_right': '55',
                'plate_type': VehicleEntry.PlateType.CAR,
                'car_model': 'Released Test',
                'car_color': 'Black',
                'driver_name': 'Released Customer',
                'driver_phone': '09125556666',
                'status': VehicleEntry.Status.ENTERED,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        vehicle = VehicleEntry.objects.get(id=response.data['id'])
        loyalty = PlateLoyaltyProfile.objects.get(tenant=self.tenant, plate_number=vehicle.plate_number)
        customer = CustomerProfile.objects.get(phone='09125556666')

        released_at = timezone.now()
        vehicle.status = VehicleEntry.Status.RELEASED
        vehicle.payment_status = VehicleEntry.PaymentStatus.PAID
        vehicle.payment_method = VehicleEntry.PaymentMethod.CASH
        vehicle.released_at = released_at
        vehicle.save(update_fields=['status', 'payment_status', 'payment_method', 'released_at', 'updated_at'])
        vehicle.job.services_total = Decimal('300000')
        vehicle.job.final_total = Decimal('300000')
        vehicle.job.worker_share_amount = Decimal('100000')
        vehicle.job.carwash_share_amount = Decimal('200000')
        vehicle.job.released_at = released_at
        vehicle.job.save(
            update_fields=[
                'services_total',
                'final_total',
                'worker_share_amount',
                'carwash_share_amount',
                'released_at',
                'updated_at',
            ]
        )
        payment = Payment.objects.create(
            tenant=self.tenant,
            vehicle_entry=vehicle,
            method=Payment.Method.CASH,
            status=Payment.Status.SUCCESS,
            amount=Decimal('300000'),
            service_amount=Decimal('300000'),
            paid_at=released_at,
        )

        reports_before = self.client.get(reverse('reports-dashboard'))
        self.assertEqual(reports_before.status_code, 200)
        self.assertEqual(reports_before.data['summary']['vehicles_count'], 1)
        self.assertEqual(reports_before.data['summary']['final_total'], 300000.0)
        self.assertEqual(reports_before.data['section_totals']['revenue']['count'], 1)

        cancel_response = self.client.patch(
            reverse('vehicle-status-update', args=[vehicle.id]),
            {'status': VehicleEntry.Status.CANCELLED},
            format='json',
        )

        self.assertEqual(cancel_response.status_code, 200)
        vehicle.refresh_from_db()
        vehicle.job.refresh_from_db()
        payment.refresh_from_db()
        loyalty.refresh_from_db()
        customer.refresh_from_db()

        self.assertEqual(vehicle.status, VehicleEntry.Status.CANCELLED)
        self.assertEqual(vehicle.payment_status, VehicleEntry.PaymentStatus.REFUNDED)
        self.assertEqual(vehicle.payment_method, '')
        self.assertIsNone(vehicle.released_at)
        self.assertIsNone(vehicle.job.released_at)
        self.assertEqual(payment.status, Payment.Status.REFUNDED)
        self.assertEqual(loyalty.visit_count, 0)
        self.assertEqual(loyalty.score, Decimal('0.0'))
        self.assertEqual(customer.yearly_score, Decimal('0.0'))

        reports_after = self.client.get(reverse('reports-dashboard'))
        self.assertEqual(reports_after.status_code, 200)
        self.assertEqual(reports_after.data['summary']['vehicles_count'], 0)
        self.assertEqual(reports_after.data['summary']['final_total'], 0.0)
        self.assertEqual(reports_after.data['section_totals']['revenue']['count'], 0)
