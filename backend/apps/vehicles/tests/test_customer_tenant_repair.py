import io
import json
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from unittest import skipUnless
from pathlib import Path
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.core.exceptions import ValidationError
from django.core.management.base import CommandError
from django.db import close_old_connections, connection, models, transaction
from django.test import TransactionTestCase

from apps.auth.models import CarWash
from apps.vehicles.customer_tenant_repair import digest, make_plan, state, unseal, fingerprint
from apps.vehicles.models import CustomerProfile, CustomerTenantRepairRun, VehicleEntry
from .guard_support import apply_plan, rollback, call_command, seed_legacy_vehicles


class CustomerRepairTests(TransactionTestCase):
    def setUp(self):
        self.a = CarWash.objects.create(pk=3, name='repair A', slug='repair-a')
        self.b = CarWash.objects.create(pk=11, name='repair B', slug='repair-b')
        self.foreign = CustomerProfile.objects.create(tenant=self.b, phone='09120000000', full_name='FOREIGN SECRET', yearly_score=5)
        self.env = patch.dict(os.environ, CUSTOMER_REPAIR_KEY=Fernet.generate_key().decode())
        self.env.start()
        self.addCleanup(self.env.stop)

    def legacy(self, phone='09121112222', tenant=None, customer=None):
        v = VehicleEntry(tenant=tenant or self.a, customer=customer or self.foreign, driver_phone=phone, driver_name='OWN SECRET', plate_number='SECRET PLATE')
        # Historical corruption must bypass the production manager explicitly.
        seed_legacy_vehicles([v])
        # MySQL does not populate AutoField IDs on bulk_create.
        return VehicleEntry.objects.order_by('-pk').first()

    def test_model_and_orm_reject_foreign_links(self):
        for operation in (
            lambda: VehicleEntry.objects.create(tenant=self.a, customer=self.foreign),
            lambda: VehicleEntry(tenant=self.a, customer=self.foreign).clean(),
            lambda: VehicleEntry.objects.bulk_create([VehicleEntry(tenant=self.a, customer=self.foreign)]),
        ):
            with self.assertRaises(ValidationError):
                operation()
        own = CustomerProfile.objects.create(tenant=self.a, phone='09123334444')
        v = VehicleEntry.objects.create(tenant=self.a, customer=own)
        for changes in ({'customer_id': self.foreign.pk}, {'tenant_id': self.b.pk}):
            with self.assertRaises(ValidationError):
                VehicleEntry.objects.filter(pk=v.pk).update(**changes)
        v.customer = self.foreign
        with self.assertRaises(ValidationError):
            VehicleEntry.objects.bulk_update([v], ['customer'])
        with self.assertRaises(ValidationError):
            v.save()
        own.tenant = self.b
        with self.assertRaises(ValidationError):
            own.save()
        with self.assertRaises(ValidationError):
            CustomerProfile.objects.filter(pk=own.pk).update(tenant=self.b)

    def test_137_links_across_tenants_dry_run_apply_and_retaining_rollback(self):
        tenant12 = CarWash.objects.create(pk=12, name='12', slug='repair-12')
        tenant20 = CarWash.objects.create(pk=20, name='20', slug='repair-20')
        tenant19 = CarWash.objects.create(pk=19, name='19', slug='repair-19')
        tenant16 = CarWash.objects.create(pk=16, name='16', slug='repair-16')
        foreign19 = CustomerProfile.objects.create(tenant=tenant19, phone='09125555555')
        foreign16 = CustomerProfile.objects.create(tenant=tenant16, phone='09126666666')
        for i in range(132):
            self.legacy(f'0912{i:07}')
        self.legacy('09120000000', tenant=tenant12)
        for i, foreign in enumerate((foreign19, foreign19, self.foreign, foreign16)):
            self.legacy(f'0913{i:07}', tenant=tenant20, customer=foreign)
        original_rows = state()
        before = digest(state())
        output = io.StringIO()
        call_command('repair_customer_tenant_links', stdout=output)
        report = json.loads(output.getvalue())
        self.assertEqual(report['repairable'], 137)
        self.assertEqual(report['proposed_profiles'], 137)
        self.assertEqual(digest(state()), before)
        self.assertFalse(CustomerTenantRepairRun.objects.exists())
        for secret in ('0912', 'OWN SECRET', 'SECRET PLATE', 'FOREIGN SECRET'):
            self.assertNotIn(secret, output.getvalue())
        plan = make_plan()
        run, changed = apply_plan(plan, digest(plan))
        self.assertEqual(changed, 137)
        self.assertEqual(CustomerProfile.objects.filter(tenant=self.a).count(), 132)
        self.assertEqual(CustomerProfile.objects.filter(tenant=tenant12).count(), 1)
        self.assertEqual(CustomerProfile.objects.filter(tenant=tenant20).count(), 4)
        for v in VehicleEntry.objects.select_related('customer'):
            self.assertEqual(v.customer.tenant_id, v.tenant_id)
            self.assertEqual(v.customer.full_name, '')
            self.assertEqual(v.customer.yearly_score, 0.5)
        created = list(CustomerProfile.objects.exclude(pk__in=[c['id'] for c in original_rows['customers']]).order_by('pk').values())
        count_before_rollback = CustomerProfile.objects.count()
        report = rollback(run)
        self.assertEqual(report['restored_links'], 137)
        self.assertEqual(len(report['retained_customers']), 137)
        self.assertEqual(set(report['unreferenced_customers']), {c['id'] for c in created})
        self.assertEqual(CustomerProfile.objects.count(), count_before_rollback)
        after = state()
        self.assertEqual(after['vehicles'], original_rows['vehicles'])
        self.assertEqual([c for c in after['customers'] if c['id'] not in report['retained_customers']], original_rows['customers'])
        self.assertEqual(list(CustomerProfile.objects.filter(pk__in=report['retained_customers']).order_by('pk').values()), created)
        self.assertEqual(VehicleEntry.objects.count(), 137)
        journal = unseal(CustomerTenantRepairRun.objects.get(pk=run).encrypted_journal)
        self.assertEqual(journal['rollback']['unreferenced_customers'], report['unreferenced_customers'])

    def test_reuse_only_local_profile_and_deduplicate_new_profiles(self):
        local = CustomerProfile.objects.create(tenant=self.a, phone='09121112222')
        self.legacy()
        self.legacy()
        plan = make_plan(self.a.pk)
        run, count = apply_plan(plan, digest(plan))
        self.assertEqual(count, 2)
        self.assertEqual(set(VehicleEntry.objects.values_list('customer_id', flat=True)), {local.pk})
        local.refresh_from_db()
        self.assertEqual(local.yearly_score, 1)
        self.assertEqual(CustomerProfile.objects.filter(tenant=self.a).count(), 1)

    def test_invalid_and_ambiguous_phone_are_skipped(self):
        self.legacy('')
        self.legacy('not a phone')
        CustomerProfile.objects.create(tenant=self.a, phone='09121112222')
        CustomerProfile.objects.create(tenant=self.a, phone='+989121112222')
        self.legacy()
        plan = make_plan()
        self.assertEqual(plan['summary']['ambiguous'], 1)
        self.assertEqual(plan['summary']['unrepairable'], 2)
        before = digest(state())
        _, count = apply_plan(plan, digest(plan))
        self.assertEqual(count, 0)
        self.assertEqual(digest(state()), before)

    def test_stale_approval_and_wrong_hash_refused(self):
        v = self.legacy()
        plan = make_plan()
        with self.assertRaises(CommandError):
            apply_plan(plan, '0' * 64)
        VehicleEntry.objects.filter(pk=v.pk).update(driver_name='changed')
        before = digest(state())
        with self.assertRaises(CommandError):
            apply_plan(plan, digest(plan))
        self.assertEqual(digest(state()), before)

    def test_changed_or_repeated_rollback_refused(self):
        self.legacy()
        plan = make_plan()
        run, _ = apply_plan(plan, digest(plan))
        VehicleEntry.objects.update(notes='new business data')
        with self.assertRaises(CommandError):
            rollback(run)
        self.assertFalse(CustomerTenantRepairRun.objects.get(pk=run).rolled_back)

    def test_failure_rolls_back_everything(self):
        self.legacy()
        plan = make_plan()
        before = digest(state())
        with patch('apps.vehicles.customer_tenant_repair.rebuild_customer_score', side_effect=RuntimeError('failure')):
            with self.assertRaises(RuntimeError):
                apply_plan(plan, digest(plan))
        self.assertEqual(digest(state()), before)
        self.assertFalse(CustomerTenantRepairRun.objects.exists())

    def test_command_encrypted_file_approval_and_journal(self):
        self.legacy()
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'plan.enc')
            output = io.StringIO()
            call_command('repair_customer_tenant_links', plan=path, stdout=output)
            report = json.loads(output.getvalue())
            self.assertNotIn(b'09121112222', Path(path).read_bytes())
            with self.assertRaises(CommandError):
                call_command('repair_customer_tenant_links', apply=True, plan=path)
            call_command('repair_customer_tenant_links', apply=True, plan=path, approve_hash=report['plan_hash'], stdout=io.StringIO())
            run = CustomerTenantRepairRun.objects.get()
            self.assertNotIn('OWN SECRET', run.encrypted_journal)
            self.assertNotIn('09121112222', run.encrypted_journal)
            call_command('repair_customer_tenant_links', rollback=run.pk, approve_hash=f'rollback:{run.pk}', stdout=io.StringIO())
            with self.assertRaises(CommandError):
                rollback(run.pk)

    def test_api_foreign_and_missing_ids_have_identical_safe_errors(self):
        from types import SimpleNamespace
        from apps.vehicles.serializers import VehicleEntrySerializer
        context = {'request': SimpleNamespace(user=SimpleNamespace(tenant_id=self.a.pk))}
        errors = []
        for value in (self.foreign.pk, 999999999):
            serializer = VehicleEntrySerializer(data={'customer_id': value}, context=context)
            self.assertFalse(serializer.is_valid())
            errors.append(serializer.errors)
        self.assertEqual(errors[0], errors[1])
        self.assertNotIn('FOREIGN SECRET', str(errors))

    def test_tenant_change_and_expression_updates_are_refused(self):
        v = VehicleEntry.objects.create(tenant=self.a)
        v.tenant = self.b
        with self.assertRaises(ValidationError):
            v.save(update_fields=['tenant'])
        with self.assertRaises(ValidationError):
            VehicleEntry.objects.update(customer_id=models.F('customer_id'))
        with self.assertRaises(ValidationError):
            CustomerProfile.objects.bulk_update([self.foreign], ['tenant'])
        with self.assertRaises(ValidationError):
            CustomerProfile.objects.bulk_create([self.foreign], update_conflicts=True,
                                                update_fields=['tenant'], unique_fields=['id'])

    def test_tampered_actions_even_with_new_hash_are_refused(self):
        self.legacy()
        plan = make_plan()
        plan['actions'][0]['kind'] = 'unrepairable'
        before = digest(state())
        with self.assertRaises(CommandError):
            apply_plan(plan, digest(plan))
        self.assertEqual(digest(state()), before)

    def test_all_standard_orm_creation_and_update_paths_are_guarded(self):
        operations = [
            lambda: VehicleEntry.objects.get_or_create(tenant=self.a, plate_number='get', defaults={'customer': self.foreign}),
            lambda: VehicleEntry.objects.update_or_create(tenant=self.a, plate_number='upsert', defaults={'customer': self.foreign}),
            lambda: VehicleEntry(tenant=self.a, customer=self.foreign).save_base(),
            lambda: VehicleEntry._base_manager.bulk_create([VehicleEntry(tenant=self.a, customer=self.foreign)]),
        ]
        for operation in operations:
            with self.assertRaises(ValidationError):
                operation()
        v = VehicleEntry.objects.create(tenant=self.a)
        with self.assertRaises(ValidationError):
            VehicleEntry.objects.update_or_create(pk=v.pk, defaults={'customer': self.foreign})
        with self.assertRaises(ValidationError):
            VehicleEntry._base_manager.filter(pk=v.pk).update(customer=self.foreign)
        with self.assertRaises(ValidationError):
            CustomerProfile.objects.update_or_create(pk=self.foreign.pk, defaults={'tenant': self.a})
        self.foreign.refresh_from_db()
        self.assertEqual(self.foreign.tenant_id, self.b.pk)
        v.refresh_from_db()
        self.assertIsNone(v.customer_id)

    def test_partial_save_cannot_hide_persisted_foreign_link(self):
        v = self.legacy()
        v.customer = CustomerProfile.objects.create(tenant=self.a, phone='09121112222')
        v.notes = 'attempt'
        with self.assertRaises(ValidationError):
            v.save(update_fields=['notes'])

    def test_replayed_plan_cannot_change_data_twice(self):
        self.legacy()
        plan = make_plan()
        apply_plan(plan, digest(plan))
        before = fingerprint()
        with self.assertRaisesMessage(CommandError, 'already applied'):
            apply_plan(plan, digest(plan))
        self.assertEqual(fingerprint(), before)
        self.assertEqual(CustomerTenantRepairRun.objects.count(), 1)

    def test_rollback_retains_profiles_and_financial_and_plate_history(self):
        from apps.payments.models import Payment
        from apps.vehicles.models import PlateLoyaltyProfile
        v = self.legacy()
        payment = Payment.objects.create(tenant=self.a, vehicle_entry=v, method='cash', amount=123,
                                         status='success', payer_name='PRIVATE PAYMENT')
        plate = PlateLoyaltyProfile.objects.create(tenant=self.a, plate_number=v.plate_number, score=3)
        original_payment = Payment.objects.values().get(pk=payment.pk)
        original_plate = PlateLoyaltyProfile.objects.values().get(pk=plate.pk)
        plan = make_plan()
        run, _ = apply_plan(plan, digest(plan))
        created = CustomerProfile.objects.get(tenant=self.a)
        original_created = CustomerProfile.objects.values().get(pk=created.pk)
        report = rollback(run)
        self.assertEqual(report['unreferenced_customers'], [created.pk])
        self.assertEqual(CustomerProfile.objects.values().get(pk=created.pk), original_created)
        self.assertEqual(Payment.objects.values().get(pk=payment.pk), original_payment)
        self.assertEqual(PlateLoyaltyProfile.objects.values().get(pk=plate.pk), original_plate)
        v.refresh_from_db()
        self.assertEqual(v.customer_id, self.foreign.pk)

    def test_new_payment_or_loyalty_change_stops_rollback(self):
        from apps.payments.models import Payment
        from apps.vehicles.models import PlateLoyaltyProfile
        v = self.legacy()
        plan = make_plan()
        run, _ = apply_plan(plan, digest(plan))
        Payment.objects.create(tenant=self.a, vehicle_entry=v, method='cash', amount=1)
        before = fingerprint()
        with self.assertRaises(CommandError):
            rollback(run)
        self.assertEqual(fingerprint(), before)
        # A separate plan/run after the new payment; then mutate plate loyalty.
        self.legacy('09121110000')
        plan = make_plan()
        run, _ = apply_plan(plan, digest(plan))
        PlateLoyaltyProfile.objects.create(tenant=self.a, plate_number='new-plate', score=2)
        with self.assertRaises(CommandError):
            rollback(run)

    def test_custom_queryset_and_raw_sql_are_guarded_on_mysql(self):
        from django.db import DatabaseError
        v = VehicleEntry.objects.create(tenant=self.a)
        if connection.vendor != 'mysql':
            # SQLite provides application protection only; explicit boundary.
            models.QuerySet(model=VehicleEntry).filter(pk=v.pk).update(customer_id=self.foreign.pk)
            return
        with self.assertRaises(DatabaseError), transaction.atomic():
            models.QuerySet(model=VehicleEntry).filter(pk=v.pk).update(customer_id=self.foreign.pk)
        with self.assertRaises(DatabaseError), transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('UPDATE vehicles_customerprofile SET tenant_id = %s WHERE id = %s', [self.a.pk, self.foreign.pk])
        self.foreign.refresh_from_db()
        self.assertEqual(self.foreign.tenant_id, self.b.pk)

    def test_dry_run_issues_no_database_writes(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        self.legacy()
        before = fingerprint()
        with CaptureQueriesContext(connection) as queries:
            call_command('repair_customer_tenant_links', dry_run=True, stdout=io.StringIO())
        for query in queries:
            self.assertTrue(query['sql'].lstrip().upper().startswith('SELECT'), query['sql'].split()[0])
        self.assertEqual(fingerprint(), before)

    def test_payment_changed_after_plan_refuses_apply(self):
        from apps.payments.models import Payment
        v = self.legacy()
        plan = make_plan()
        Payment.objects.create(tenant=self.a, vehicle_entry=v, method='cash', amount=1)
        before = fingerprint()
        with self.assertRaises(CommandError):
            apply_plan(plan, digest(plan))
        self.assertEqual(fingerprint(), before)
        self.assertFalse(CustomerTenantRepairRun.objects.exists())

    def test_legacy_journal_requires_review_and_never_deletes(self):
        from apps.vehicles.customer_tenant_repair import seal
        self.legacy()
        plan = make_plan()
        run_id, _ = apply_plan(plan, digest(plan))
        run = CustomerTenantRepairRun.objects.get(pk=run_id)
        journal = unseal(run.encrypted_journal)
        journal.pop('version')
        run.encrypted_journal = seal(journal)
        run.save(update_fields=['encrypted_journal'])
        before = fingerprint()
        with self.assertRaisesMessage(CommandError, 'Legacy journal'):
            rollback(run_id)
        self.assertEqual(fingerprint(), before)


@skipUnless(connection.vendor == 'mysql', 'Requires isolated MySQL/InnoDB row locks')
class MySQLRepairConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.a = CarWash.objects.create(name='Concurrent A', slug='concurrent-repair-a')
        self.b = CarWash.objects.create(name='Concurrent B', slug='concurrent-repair-b')
        self.customer = CustomerProfile.objects.create(tenant=self.a, phone='09121112222')
        key = patch.dict(os.environ, CUSTOMER_REPAIR_KEY=Fernet.generate_key().decode())
        key.start()
        self.addCleanup(key.stop)

    def test_parallel_apply_commits_exactly_once(self):
        seed_legacy_vehicles([
            VehicleEntry(tenant=self.b, customer=self.customer, driver_phone=self.customer.phone)
        ])
        plan = make_plan()
        barrier = Barrier(2)
        def apply(_):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    apply_plan(plan, digest(plan))
                    return 'applied'
                except CommandError:
                    return 'refused'
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(apply, range(2)))
        self.assertCountEqual(results, ['applied', 'refused'])
        self.assertEqual(CustomerTenantRepairRun.objects.count(), 1)
        self.assertEqual(CustomerProfile.objects.filter(tenant=self.b).count(), 1)
        v = VehicleEntry.objects.select_related('customer').get()
        self.assertEqual(v.customer.tenant_id, v.tenant_id)

    def test_customer_lock_serializes_then_refuses_ownership_transfer(self):
        started, done = Event(), Event()
        def transfer():
            close_old_connections()
            try:
                customer = CustomerProfile.objects.get(pk=self.customer.pk)
                customer.tenant_id = self.b.pk
                started.set()
                try:
                    customer.save(update_fields=['tenant'])
                except ValidationError:
                    return 'refused'
                return 'changed'
            finally:
                done.set()
                close_old_connections()
        with ThreadPoolExecutor(max_workers=1) as executor:
            with transaction.atomic():
                CustomerProfile.objects.select_for_update().get(pk=self.customer.pk)
                future = executor.submit(transfer)
                self.assertTrue(started.wait(timeout=10))
                self.assertFalse(done.wait(timeout=0.2))
                VehicleEntry.objects.create(tenant=self.a, customer=self.customer)
            self.assertEqual(future.result(timeout=10), 'refused')
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.tenant_id, self.a.pk)
        self.assertEqual(VehicleEntry.objects.get().customer_id, self.customer.pk)

    def test_large_synthetic_plan_and_apply_resource_measurement(self):
        import time
        import tracemalloc
        # Match the observed row scale using entirely synthetic data.
        VehicleEntry.objects.bulk_create([
            VehicleEntry(tenant=self.a, plate_number=f'benchmark-{i}') for i in range(21276)
        ], batch_size=500)
        seed_legacy_vehicles([
            VehicleEntry(tenant=self.b, customer=self.customer, driver_phone=f'0912{i:07}')
            for i in range(137)
        ])
        tracemalloc.start()
        try:
            start = time.monotonic()
            plan = make_plan()
            plan_seconds = time.monotonic() - start
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        self.assertEqual(plan['summary']['repairable'], 137)
        self.assertEqual(VehicleEntry.objects.count(), 21413)
        start = time.monotonic()
        _, changed = apply_plan(plan, digest(plan))
        apply_seconds = time.monotonic() - start
        self.assertEqual(changed, 137)
        print(f'SYNTHETIC_REPAIR_METRICS rows=21413 plan_seconds={plan_seconds:.3f} '
              f'plan_python_peak_bytes={peak} apply_transaction_seconds={apply_seconds:.3f}')

    def test_repair_range_locks_block_new_unassigned_profiles(self):
        from apps.vehicles.customer_tenant_repair import repair_transaction
        started, done = Event(), Event()
        def insert():
            close_old_connections()
            try:
                started.set()
                return CustomerProfile.objects.create(tenant=None, phone='09129990000').pk
            finally:
                done.set()
                close_old_connections()
        with ThreadPoolExecutor(max_workers=1) as executor:
            with repair_transaction():
                fingerprint(lock=True)
                future = executor.submit(insert)
                self.assertTrue(started.wait(timeout=10))
                self.assertFalse(done.wait(timeout=0.2))
            self.assertIsNotNone(future.result(timeout=10))
        # The session default was not changed for ordinary application writes.
        with connection.cursor() as cursor:
            cursor.execute('SELECT @@transaction_isolation')
            self.assertEqual(cursor.fetchone()[0], 'READ-COMMITTED')
