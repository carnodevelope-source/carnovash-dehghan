import io
import json
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from types import SimpleNamespace
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.db import IntegrityError, close_old_connections, transaction
from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from apps.auth.models import CarWash, User
from apps.vehicles.loyalty import rebuild_customer_score
from apps.vehicles.models import CustomerProfile, VehicleEntry
from apps.vehicles.serializers import VehicleEntrySerializer


class CustomerTenantIsolationTests(APITestCase):
    def setUp(self):
        self.a = CarWash.objects.create(name='A', slug='customer-isolation-a')
        self.b = CarWash.objects.create(name='B', slug='customer-isolation-b')
        self.ua = User.objects.create_user(username='customer-a', tenant=self.a, role='manager')
        self.ub = User.objects.create_user(username='customer-b', tenant=self.b, role='manager')
        self.phone = '09120001234'

    def create_vehicle(self, user, phone=None):
        self.client.force_authenticate(user)
        response = self.client.post(reverse('vehicle-list-create'), {
            'plate_number': f'55 B 123 {user.tenant_id:02}', 'plate_left': '55', 'plate_letter': 'B',
            'plate_mid': '123', 'plate_right': f'{user.tenant_id:02}',
            'car_model': 'test', 'car_color': 'white', 'driver_name': 'test customer',
            'driver_phone': phone or self.phone,
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        return VehicleEntry.objects.get(pk=response.data['id'])

    def test_same_phone_creates_independent_profiles_and_scores(self):
        first = self.create_vehicle(self.ua)
        second = self.create_vehicle(self.ub)
        self.assertNotEqual(first.customer_id, second.customer_id)
        self.assertEqual(first.customer.tenant_id, self.a.pk)
        self.assertEqual(second.customer.tenant_id, self.b.pk)
        self.assertEqual(CustomerProfile.objects.filter(phone=self.phone).count(), 2)
        VehicleEntrySerializer()._resolve_customer_profile(self.phone, tenant=self.a, increment_visit=True)
        first.customer.refresh_from_db()
        second.customer.refresh_from_db()
        self.assertEqual(first.customer.yearly_score, Decimal('1.0'))
        self.assertEqual(second.customer.yearly_score, Decimal('0.5'))

    def test_database_rejects_duplicate_only_within_same_tenant(self):
        CustomerProfile.objects.create(tenant=self.a, phone=self.phone)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CustomerProfile.objects.create(tenant=self.a, phone=self.phone)
        CustomerProfile.objects.create(tenant=self.b, phone=self.phone)

    def test_unassigned_legacy_profile_is_never_claimed_or_resolved(self):
        orphan = CustomerProfile.objects.create(tenant=None, phone=self.phone, full_name='legacy', yearly_score=5)
        vehicle = self.create_vehicle(self.ua)
        self.assertNotEqual(vehicle.customer_id, orphan.pk)
        orphan.refresh_from_db()
        self.assertIsNone(orphan.tenant_id)
        self.assertEqual(orphan.full_name, 'legacy')
        self.assertEqual(orphan.yearly_score, 5)
        with self.assertRaises(ValidationError):
            VehicleEntrySerializer()._resolve_customer_profile(self.phone, tenant=None)

    def test_edit_resolves_only_own_profile_and_can_clear_phone(self):
        vehicle = self.create_vehicle(self.ua)
        other_phone = '09120009999'
        foreign = CustomerProfile.objects.create(tenant=self.b, phone=other_phone, full_name='private')
        serializer = VehicleEntrySerializer(vehicle, context={'request': SimpleNamespace(user=self.ua)})
        vehicle = serializer.update(vehicle, {'driver_phone': other_phone, 'driver_name': 'own'})
        self.assertEqual(vehicle.customer.tenant_id, self.a.pk)
        self.assertNotEqual(vehicle.customer_id, foreign.pk)
        foreign.refresh_from_db()
        self.assertEqual(foreign.full_name, 'private')
        serializer.update(vehicle, {'driver_phone': ''})
        vehicle.refresh_from_db()
        self.assertIsNone(vehicle.customer_id)

    def test_rebuild_excludes_historical_foreign_visits(self):
        vehicle = self.create_vehicle(self.ua)
        VehicleEntry.objects.create(tenant=self.b, customer=vehicle.customer, plate_number='foreign')
        rebuild_customer_score(vehicle.customer)
        vehicle.customer.refresh_from_db()
        self.assertEqual(vehicle.customer.yearly_score, Decimal('0.5'))

    def test_existing_bad_link_is_not_silently_repaired_on_edit(self):
        vehicle = self.create_vehicle(self.ua)
        foreign = CustomerProfile.objects.create(tenant=self.b, phone='09121110000')
        VehicleEntry.objects.filter(pk=vehicle.pk).update(customer=foreign)
        vehicle.refresh_from_db()
        serializer = VehicleEntrySerializer(vehicle, context={'request': SimpleNamespace(user=self.ua)})
        with self.assertRaises(ValidationError):
            serializer.update(vehicle, {'driver_name': 'new'})
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.customer_id, foreign.pk)

    def test_audit_counts_all_132_bad_links_without_pii_or_writes(self):
        foreign = CustomerProfile.objects.create(tenant=self.b, phone=self.phone, full_name='DO NOT PRINT')
        VehicleEntry.objects.bulk_create([
            VehicleEntry(tenant=self.a, customer=foreign, plate_number=f'private-{i}', driver_phone=self.phone)
            for i in range(132)
        ])
        output = io.StringIO()
        call_command('audit_customer_tenant_links', tenant=self.a.pk, customer_id=foreign.pk, stdout=output)
        result = json.loads(output.getvalue())
        self.assertEqual(result['mismatched_vehicle_count'], 132)
        self.assertEqual(result['changed_records'], 0)
        for secret in (self.phone, foreign.full_name, 'private-'):
            self.assertNotIn(secret, output.getvalue())
        self.assertEqual(VehicleEntry.objects.filter(customer=foreign, tenant=self.a).count(), 132)

    def test_create_integrity_failure_becomes_controlled_validation_error(self):
        with patch('django.db.models.query.QuerySet.get_or_create', side_effect=IntegrityError('private SQL')):
            with self.assertRaises(ValidationError) as error:
                VehicleEntrySerializer()._resolve_customer_profile(self.phone, tenant=self.a)
        self.assertNotIn('private SQL', str(error.exception))


@skipUnless(settings.DATABASES['default']['ENGINE'].endswith('mysql'), 'Real concurrent insert test requires MySQL')
class ConcurrentCustomerTests(TransactionTestCase):
    def test_two_connections_create_one_customer_and_keep_both_visit_increments(self):
        tenant = CarWash.objects.create(name='Concurrent', slug='concurrent-customer')
        barrier = Barrier(2)
        def resolve(_):
            close_old_connections()
            try:
                owned_tenant = CarWash.objects.get(pk=tenant.pk)
                barrier.wait(timeout=10)
                return VehicleEntrySerializer()._resolve_customer_profile(
                    '09121112222', tenant=owned_tenant, increment_visit=True,
                ).pk
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as executor:
            ids = list(executor.map(resolve, range(2)))
        self.assertEqual(ids[0], ids[1])
        self.assertEqual(CustomerProfile.objects.get(pk=ids[0]).yearly_score, Decimal('1.0'))
