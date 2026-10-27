import io
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import models
from django.test import TestCase

from apps.auth.models import CarWash
from apps.vehicles.customer_tenant_repair import apply_plan, digest, make_plan, rollback, state
from apps.vehicles.models import CustomerProfile, CustomerTenantRepairRun, VehicleEntry


class CustomerRepairTests(TestCase):
    def setUp(self):
        self.a = CarWash.objects.create(name='repair A', slug='repair-a')
        self.b = CarWash.objects.create(name='repair B', slug='repair-b')
        self.foreign = CustomerProfile.objects.create(tenant=self.b, phone='09120000000', full_name='FOREIGN SECRET', yearly_score=5)
        self.env = patch.dict(os.environ, CUSTOMER_REPAIR_KEY=Fernet.generate_key().decode())
        self.env.start()
        self.addCleanup(self.env.stop)

    def legacy(self, phone='09121112222'):
        v = VehicleEntry(tenant=self.a, customer=self.foreign, driver_phone=phone, driver_name='OWN SECRET', plate_number='SECRET PLATE')
        # Historical corruption must bypass the production manager explicitly.
        models.QuerySet(model=VehicleEntry).bulk_create([v])
        return v

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

    def test_137_links_dry_run_apply_and_exact_rollback(self):
        for i in range(137):
            self.legacy(f'0912{i:07}')
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
        self.assertEqual(CustomerProfile.objects.filter(tenant=self.a).count(), 137)
        for v in VehicleEntry.objects.select_related('customer'):
            self.assertEqual(v.customer.tenant_id, v.tenant_id)
            self.assertEqual(v.customer.full_name, '')
            self.assertEqual(v.customer.yearly_score, 0.5)
        rollback(run)
        self.assertEqual(digest(state()), before)
        self.assertEqual(VehicleEntry.objects.count(), 137)

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
