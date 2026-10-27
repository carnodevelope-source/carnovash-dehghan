from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class CustomerTenantMigrationTests(TransactionTestCase):
    def test_0025_preserves_existing_unassigned_customer_and_bad_links(self):
        previous = ('vehicles', '0024_alter_vehiclejob_worker_payment_type')
        latest = ('vehicles', '0025_customer_phone_per_tenant')
        executor = MigrationExecutor(connection)
        restore_targets = executor.loader.graph.leaf_nodes()
        executor.migrate([previous])
        try:
            old = executor.loader.project_state([previous]).apps
            from apps.auth.models import CarWash as Tenant
            Customer = old.get_model('vehicles', 'CustomerProfile')
            Vehicle = old.get_model('vehicles', 'VehicleEntry')
            source = Tenant.objects.create(name='source', slug='migration-source')
            other = Tenant.objects.create(name='other', slug='migration-other')
            customer = Customer.objects.create(tenant_id=other.pk, phone='09121110000', yearly_score=3)
            orphan = Customer.objects.create(tenant=None, phone='09121110001')
            vehicle = Vehicle.objects.create(tenant_id=source.pk, customer=customer, plate_number='legacy')
            executor = MigrationExecutor(connection)
            executor.migrate([latest])
            from apps.vehicles.models import CustomerProfile, VehicleEntry
            self.assertEqual(VehicleEntry.objects.get(pk=vehicle.pk).customer_id, customer.pk)
            self.assertIsNone(CustomerProfile.objects.get(pk=orphan.pk).tenant_id)
            self.assertEqual(CustomerProfile.objects.get(pk=customer.pk).yearly_score, 3)
            # New schema permits the phone in the other tenant, without rewriting
            # the previously shared customer or any vehicle relationship.
            CustomerProfile.objects.create(tenant=source, phone=customer.phone)
        finally:
            MigrationExecutor(connection).migrate(restore_targets)
