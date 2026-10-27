import io
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from unittest import skipUnless
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.db import DatabaseError, close_old_connections, connection, connections, models, transaction
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from apps.auth.models import CarWash
from apps.payments.models import Payment
from apps.vehicles import mysql_guards as guards
from apps.vehicles.customer_tenant_repair import apply_plan, rollback, make_plan, digest, fingerprint
from apps.vehicles.models import CustomerProfile, CustomerTenantAuthorization, CustomerTenantRepairRun, VehicleEntry
from .guard_support import database_account, seed_legacy_vehicles


@skipUnless(connection.vendor == 'mysql', 'MySQL 8.4 security integration suite')
class MySQLDatabaseGuardTests(TransactionTestCase):
    databases = {'default', 'recovery'}

    def setUp(self):
        self.a = CarWash.objects.create(name='A', slug='guard-a')
        self.b = CarWash.objects.create(name='B', slug='guard-b')
        self.own = CustomerProfile.objects.create(tenant=self.a, phone='09121112222')
        self.foreign = CustomerProfile.objects.create(tenant=self.b, phone='09129990000', full_name='FOREIGN PRIVATE NAME')
        self.vehicle = VehicleEntry.objects.create(tenant=self.a, customer=self.own, plate_number='own')
        key = patch.dict(os.environ, CUSTOMER_REPAIR_KEY=Fernet.generate_key().decode())
        key.start()
        self.addCleanup(key.stop)

    def query(self, sql, params=()):
        with connection.cursor() as cursor:
            cursor.execute(sql, params or None)

    def reject(self, sql, params=()):
        with self.assertRaises(DatabaseError) as caught, transaction.atomic():
            self.query(sql, params)
        self.assertEqual(caught.exception.args, (1644, guards.ERROR))
        self.assertNotIn(self.foreign.full_name, str(caught.exception))
        self.assertNotIn(self.foreign.phone, str(caught.exception))

    def test_plain_insert_and_explicit_model_save_base_reject_foreign(self):
        columns = [f.column for f in VehicleEntry._meta.local_fields if not f.primary_key]
        names = ','.join(guards.identifier(c) for c in columns)
        values = ','.join('%s' if c == 'customer_id' else guards.identifier(c) for c in columns)
        direct_insert = f'INSERT INTO vehicles_vehicleentry ({names}) SELECT {values} FROM vehicles_vehicleentry WHERE id=%s'
        with database_account('app'):
            for operation in (
                lambda: self.query(direct_insert, [self.foreign.pk, self.vehicle.pk]),
                lambda: models.QuerySet(model=VehicleEntry).bulk_create([VehicleEntry(tenant=self.a, customer=self.foreign)]),
                lambda: models.Model.save_base(VehicleEntry(tenant=self.a, customer=self.foreign)),
            ):
                with self.assertRaises(DatabaseError) as error, transaction.atomic():
                    operation()
                self.assertEqual(error.exception.args, (1644, guards.ERROR))

    def test_sql_update_custom_queryset_tenant_change_and_session_flags_rejected(self):
        with database_account('app'):
            self.reject('UPDATE vehicles_vehicleentry SET customer_id=%s WHERE id=%s', [self.foreign.pk, self.vehicle.pk])
            self.reject('UPDATE vehicles_vehicleentry SET tenant_id=%s WHERE id=%s', [self.b.pk, self.vehicle.pk])
            self.reject('UPDATE vehicles_vehicleentry SET tenant_id=%s, customer_id=%s WHERE id=%s', [self.b.pk, self.foreign.pk, self.vehicle.pk])
            with self.assertRaises(DatabaseError), transaction.atomic():
                models.QuerySet(model=VehicleEntry).filter(pk=self.vehicle.pk).update(customer_id=self.foreign.pk)
            self.query('SET @customer_repair_authorized=1')
            self.query('SET FOREIGN_KEY_CHECKS=0')
            try:
                self.reject('UPDATE vehicles_vehicleentry SET customer_id=%s WHERE id=%s', [self.foreign.pk, self.vehicle.pk])
                self.reject('UPDATE vehicles_vehicleentry SET customer_id=999999999 WHERE id=%s', [self.vehicle.pk])
            finally:
                self.query('SET FOREIGN_KEY_CHECKS=1')

    def test_null_policy_customer_identity_and_deletion(self):
        orphan = CustomerProfile.objects.create(phone='09123330000')
        with database_account('app'):
            for params in ([None, self.own.pk], [self.a.pk, orphan.pk], [None, orphan.pk]):
                with self.assertRaises(DatabaseError), transaction.atomic():
                    models.QuerySet(model=VehicleEntry).bulk_create([VehicleEntry(tenant_id=params[0], customer_id=params[1])])
            for pk, tenant in ((self.own.pk, self.b.pk), (self.own.pk, None), (orphan.pk, self.a.pk)):
                self.reject('UPDATE vehicles_customerprofile SET tenant_id=%s WHERE id=%s', [tenant, pk])
            self.reject('UPDATE vehicles_customerprofile SET id=id+100000 WHERE id=%s', [self.own.pk])
            self.reject('UPDATE vehicles_vehicleentry SET id=id+100000 WHERE id=%s', [self.vehicle.pk])
            self.reject('DELETE FROM vehicles_customerprofile WHERE id=%s', [self.own.pk])
            self.query('UPDATE vehicles_customerprofile SET full_name=%s, phone=%s WHERE id=%s', ['permitted', '09121110000', self.own.pk])
            models.QuerySet(model=VehicleEntry).bulk_create([VehicleEntry(tenant=None, customer=None)])

    def test_legacy_read_unrelated_update_and_valid_repair(self):
        legacy = VehicleEntry(tenant=self.a, customer=self.foreign, driver_phone=self.own.phone)
        seed_legacy_vehicles([legacy])
        with database_account('app'):
            self.assertEqual(VehicleEntry.objects.get(pk=legacy.pk).customer_id, self.foreign.pk)
            self.query('UPDATE vehicles_vehicleentry SET notes=%s WHERE id=%s', ['permitted historical edit', legacy.pk])
            self.query('UPDATE vehicles_vehicleentry SET customer_id=%s WHERE id=%s', [self.own.pk, legacy.pk])
            self.reject('UPDATE vehicles_vehicleentry SET customer_id=%s WHERE id=%s', [self.foreign.pk, legacy.pk])

    def test_ordinary_account_cannot_issue_maintenance_or_ddl_or_execute(self):
        self.query('CREATE PROCEDURE cw_guard_test_probe() SQL SECURITY DEFINER SELECT 1')
        try:
            with database_account('app'):
                for sql in (
                    f'DROP TRIGGER {guards.PREFIX}vehicle_bu',
                    'TRUNCATE TABLE vehicles_customerprofile',
                    'INSERT INTO vehicles_customertenantauthorization (id) VALUES (1)',
                    'UPDATE vehicles_customertenantauthorization SET consumed_at=NULL',
                    'INSERT INTO vehicles_customertenantrepairrun (id) VALUES (1)',
                    'CALL cw_guard_test_probe()',
                ):
                    with self.assertRaises(DatabaseError), transaction.atomic():
                        self.query(sql)
                with self.assertRaises(ImproperlyConfigured):
                    apply_plan(make_plan(), digest(make_plan()))
        finally:
            self.query('DROP PROCEDURE cw_guard_test_probe')

    def test_maintenance_grants_are_minimal_and_no_definer_login(self):
        with database_account('maint'):
            guards.require_maintenance(connection)
            for sql in (
                f'DROP TRIGGER {guards.PREFIX}vehicle_bu',
                'DELETE FROM vehicles_customertenantauthorization',
                'UPDATE vehicles_customertenantauthorization SET consumed_at=NULL',
                'UPDATE vehicles_customerprofile SET tenant_id=tenant_id',
                'UPDATE vehicles_vehicleentry SET notes=notes',
                'UPDATE payments_payment SET amount=amount',
                'CREATE TABLE guard_forbidden (id INT)',
            ):
                with self.assertRaises(DatabaseError), transaction.atomic():
                    self.query(sql)
        with connection.cursor() as cursor:
            cursor.execute('SELECT account_locked FROM mysql.user WHERE User=%s AND Host=%s', [guards.definer_user(connection.settings_dict['NAME']), 'localhost'])
            self.assertEqual(cursor.fetchone()[0], 'Y')

    def test_one_use_authorization_bound_to_connection_and_exact_row(self):
        with database_account('maint'):
            with connection.cursor() as cursor:
                cursor.execute('SELECT CONNECTION_ID()')
                cid = cursor.fetchone()[0]
            token = CustomerTenantAuthorization.objects.create(
                connection_id=cid, vehicle_id=self.vehicle.pk, tenant_id=self.a.pk,
                from_customer_id=self.own.pk, to_customer_id=self.foreign.pk,
                repair_run_id=12345, plan_hash='f' * 64, expires_at=timezone.now()+timedelta(minutes=1))
            # Another connection cannot reuse the issued token.
            def attempt():
                close_old_connections()
                try:
                    with database_account('app'):
                        try:
                            self.query('UPDATE vehicles_vehicleentry SET customer_id=%s WHERE id=%s', [self.foreign.pk, self.vehicle.pk])
                            return False
                        except DatabaseError:
                            return True
                finally:
                    close_old_connections()
            with ThreadPoolExecutor(max_workers=1) as pool:
                self.assertTrue(pool.submit(attempt).result(timeout=10))
            self.query('UPDATE vehicles_vehicleentry SET customer_id=%s WHERE id=%s', [self.foreign.pk, self.vehicle.pk])
            self.assertIsNotNone(CustomerTenantAuthorization.objects.get(pk=token.pk).consumed_at)
            self.query('UPDATE vehicles_vehicleentry SET customer_id=%s WHERE id=%s', [self.own.pk, self.vehicle.pk])
            self.reject('UPDATE vehicles_vehicleentry SET customer_id=%s WHERE id=%s', [self.foreign.pk, self.vehicle.pk])

    def test_approved_apply_and_rollback_with_restricted_account_and_payments(self):
        legacy = VehicleEntry(tenant=self.a, customer=self.foreign, driver_phone='09123334444')
        seed_legacy_vehicles([legacy])
        payment = Payment.objects.create(tenant=self.a, vehicle_entry=legacy, method='cash', amount=123)
        before_payment = Payment.objects.values().get(pk=payment.pk)
        plan = make_plan(self.a.pk)
        with database_account('maint'):
            run, changed = apply_plan(plan, digest(plan))
            self.assertEqual(changed, 1)
            before_count = CustomerProfile.objects.count()
            report = rollback(run)
            self.assertEqual(CustomerProfile.objects.count(), before_count)
            self.assertEqual(report['restored_links'], 1)
            self.assertEqual(CustomerTenantAuthorization.objects.filter(repair_run_id=run, consumed_at__isnull=False).count(), 1)
        self.assertEqual(Payment.objects.values().get(pk=payment.pk), before_payment)
        self.assertEqual(VehicleEntry.objects.get(pk=legacy.pk).customer_id, self.foreign.pk)

    def test_migration_reinstall_reverse_and_legacy_preservation(self):
        before = fingerprint()
        try:
            guards.install(connection)
            guards.uninstall(connection)
            # Represents rows that existed before installing the guard.
            self.query('UPDATE vehicles_vehicleentry SET customer_id=%s WHERE id=%s', [self.foreign.pk, self.vehicle.pk])
            guards.install(connection)
            guards.install(connection)
            with database_account('app'):
                self.query('UPDATE vehicles_vehicleentry SET notes=%s WHERE id=%s', ['historical', self.vehicle.pk])
                self.reject('UPDATE vehicles_vehicleentry SET customer_id=%s WHERE id=%s', [self.foreign.pk, VehicleEntry.objects.create(tenant=self.a).pk])
            with connection.cursor() as cursor:
                self.assertEqual(len(guards.verify_existing(cursor, connection.settings_dict['NAME'])), 4)
        finally:
            guards.install(connection)
        self.assertEqual(VehicleEntry.objects.get(pk=self.vehicle.pk).customer_id, self.foreign.pk)

    def test_partial_ddl_failure_compensates_and_retry_succeeds(self):
        before = fingerprint()
        guards.uninstall(connection)
        def fail(execute, sql, params, many, context):
            if sql.startswith('CREATE DEFINER=') and guards.PREFIX+'vehicle_bu' in sql:
                raise RuntimeError('synthetic DDL interruption')
            return execute(sql, params, many, context)
        try:
            with connection.execute_wrapper(fail):
                with self.assertRaises(RuntimeError):
                    guards.install(connection)
            with connection.cursor() as cursor:
                self.assertEqual(guards.installed(cursor), {})
            self.assertEqual(fingerprint(), before)
        finally:
            guards.install(connection)

    def test_preflight_unsafe_app_account_rejected_before_ddl(self):
        with connection.cursor() as cursor:
            before = guards.installed(cursor)
        with override_settings(CUSTOMER_TENANT_GUARD_APP_ACCOUNT=connection.settings_dict['USER']+'@%'):
            with self.assertRaises((ImproperlyConfigured, DatabaseError)):
                guards.install(connection)
        with connection.cursor() as cursor:
            self.assertEqual(guards.installed(cursor), before)

    def test_concurrent_customer_ownership_transfer_rejected_after_lock(self):
        started, finished = Event(), Event()
        def transfer():
            close_old_connections()
            try:
                with database_account('app'):
                    started.set()
                    try:
                        self.query('UPDATE vehicles_customerprofile SET tenant_id=%s WHERE id=%s', [self.b.pk, self.own.pk])
                    except DatabaseError:
                        return 'rejected'
                    return 'unsafe'
            finally:
                finished.set()
                close_old_connections()
        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction.atomic():
                CustomerProfile.objects.select_for_update().get(pk=self.own.pk)
                future = pool.submit(transfer)
                self.assertTrue(started.wait(timeout=10))
                self.assertFalse(finished.wait(timeout=.2))
            self.assertEqual(future.result(timeout=10), 'rejected')

    def test_restore_account_has_no_maintenance_capability(self):
        with database_account('restore', alias='recovery'):
            with connections['recovery'].cursor() as cursor:
                with self.assertRaises(DatabaseError):
                    cursor.execute('INSERT INTO vehicles_customertenantauthorization (id) VALUES (1)')
                with self.assertRaises(DatabaseError):
                    cursor.execute(f'DROP TRIGGER {guards.PREFIX}vehicle_bi')

    def test_guard_error_is_controlled_by_existing_api_handler(self):
        from config.api import exception_handler
        response = exception_handler(DatabaseError(1644, guards.ERROR), {})
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('FOREIGN PRIVATE NAME', str(response.data))

    def test_expired_and_wrong_transition_permissions_do_not_authorize(self):
        with database_account('maint'):
            with connection.cursor() as cursor:
                cursor.execute('SELECT CONNECTION_ID()')
                cid = cursor.fetchone()[0]
            CustomerTenantAuthorization.objects.create(
                connection_id=cid, vehicle_id=self.vehicle.pk, tenant_id=self.a.pk,
                from_customer_id=self.own.pk, to_customer_id=self.foreign.pk,
                repair_run_id=10001, plan_hash='a'*64, expires_at=timezone.now()-timedelta(seconds=1))
            self.reject('UPDATE vehicles_vehicleentry SET customer_id=%s WHERE id=%s', [self.foreign.pk, self.vehicle.pk])
            CustomerTenantAuthorization.objects.create(
                connection_id=cid, vehicle_id=self.vehicle.pk, tenant_id=self.b.pk,
                from_customer_id=self.own.pk, to_customer_id=self.foreign.pk,
                repair_run_id=10002, plan_hash='b'*64, expires_at=timezone.now()+timedelta(minutes=1))
            self.reject('UPDATE vehicles_vehicleentry SET customer_id=%s WHERE id=%s', [self.foreign.pk, self.vehicle.pk])
            self.assertFalse(CustomerTenantAuthorization.objects.filter(consumed_at__isnull=False).exists())

    def test_multirow_sql_failure_is_atomic(self):
        other = VehicleEntry.objects.create(tenant=self.b, customer=self.foreign)
        target = CustomerProfile.objects.create(tenant=self.a, phone='09124445555')
        with database_account('app'):
            self.reject('UPDATE vehicles_vehicleentry SET customer_id=%s WHERE id IN (%s,%s)', [target.pk, self.vehicle.pk, other.pk])
        self.vehicle.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(self.vehicle.customer_id, self.own.pk)
        self.assertEqual(other.customer_id, self.foreign.pk)

    def test_unreviewed_before_trigger_fails_preflight(self):
        self.query('CREATE TRIGGER guard_unreviewed BEFORE UPDATE ON vehicles_vehicleentry FOR EACH ROW SET NEW.notes=OLD.notes')
        try:
            with self.assertRaises(ImproperlyConfigured):
                guards.install(connection)
        finally:
            self.query('DROP TRIGGER guard_unreviewed')
        with connection.cursor() as cursor:
            self.assertEqual(len(guards.verify_existing(cursor, connection.settings_dict['NAME'])), 4)

    def test_reverse_failure_restores_removed_guards(self):
        def fail(execute, sql, params, many, context):
            if sql == f'DROP TRIGGER `{guards.PREFIX}vehicle_bi`':
                raise RuntimeError('synthetic reverse interruption')
            return execute(sql, params, many, context)
        with connection.execute_wrapper(fail):
            with self.assertRaises(RuntimeError):
                guards.uninstall(connection)
        with connection.cursor() as cursor:
            self.assertEqual(len(guards.verify_existing(cursor, connection.settings_dict['NAME'])), 4)

    def test_real_isolated_restore_under_account_without_bypass(self):
        import json
        import tempfile
        from pathlib import Path
        from apps.cloud_backup.archive import restore_fixture
        from apps.cloud_backup.snapshot import collect
        fixture, _ = collect(self.a.pk)
        self.assertNotIn(b'customertenantauthorization', fixture)
        self.assertNotIn(b'customertenantrepairrun', fixture)
        self.assertNotIn(self.foreign.full_name.encode(), fixture)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'fixture.json'
            path.write_bytes(fixture)
            with database_account('restore', alias='recovery'):
                restore_fixture(path, self.a.pk, 'recovery')
                restored = VehicleEntry.objects.using('recovery').get(pk=self.vehicle.pk)
                self.assertEqual(restored.customer.tenant_id, restored.tenant_id)
                with connections['recovery'].cursor() as cursor:
                    with self.assertRaises(DatabaseError):
                        cursor.execute('INSERT INTO vehicles_customertenantauthorization (id) VALUES (1)')

    def test_actual_application_connection_rejects_dba_credentials(self):
        connection.close()
        try:
            with override_settings(CUSTOMER_TENANT_GUARD_ROLE='application'):
                for _ in range(2):
                    with self.assertRaises(ImproperlyConfigured):
                        connection.ensure_connection()
                    self.assertIsNone(connection.connection)
        finally:
            connection.close()
        with override_settings(CUSTOMER_TENANT_GUARD_ROLE='application'):
            with database_account('app'):
                self.query('SELECT 1')
                self.assertTrue(connection.is_usable())
        with override_settings(CUSTOMER_TENANT_GUARD_ROLE='maintenance'):
            with database_account('maint'):
                self.query('SELECT 1')

    def test_read_only_deployment_audit(self):
        from django.test.utils import CaptureQueriesContext
        output = io.StringIO()
        with CaptureQueriesContext(connection) as queries:
            call_command('check_customer_tenant_guards', stdout=output)
        self.assertIn('"status": "verified"', output.getvalue())
        for query in queries:
            self.assertIn(query['sql'].split()[0].upper(), {'SELECT', 'SHOW'})

    def test_ca8a896_historical_model_writes_remain_compatible(self):
        from django.db.migrations.executor import MigrationExecutor
        old_apps = MigrationExecutor(connection).loader.project_state([
            ('vehicles', '0025_customer_phone_per_tenant')]).apps
        OldVehicle = old_apps.get_model('vehicles', 'VehicleEntry')
        with database_account('app'):
            vehicle = OldVehicle.objects.create(tenant_id=self.a.pk, customer_id=self.own.pk,
                                               plate_number='old-code', driver_phone=self.own.phone)
            vehicle.notes = 'compatible ordinary update'
            vehicle.save()
            with self.assertRaises(DatabaseError) as error, transaction.atomic():
                OldVehicle.objects.create(tenant_id=self.a.pk, customer_id=self.foreign.pk,
                                          plate_number='rejected-old-code')
            self.assertEqual(error.exception.args, (1644, guards.ERROR))
        self.assertEqual(VehicleEntry.objects.get(pk=vehicle.pk).customer_id, self.own.pk)

    def test_failed_rollback_reverts_links_and_consumed_permissions_atomically(self):
        from apps.vehicles.customer_tenant_repair import authorize_rollback
        legacy = [VehicleEntry(tenant=self.a, customer=self.foreign, driver_phone=f'0912333444{i}') for i in range(2)]
        seed_legacy_vehicles(legacy)
        plan = make_plan()
        with database_account('maint'):
            run, _ = apply_plan(plan, digest(plan))
            before = fingerprint()
            journal = CustomerTenantRepairRun.objects.get(pk=run).encrypted_journal
            calls = []
            def fail_second(run_obj, change):
                calls.append(change['vehicle'])
                if len(calls) == 2:
                    raise RuntimeError('synthetic rollback interruption')
                return authorize_rollback(run_obj, change)
            with patch('apps.vehicles.customer_tenant_repair.authorize_rollback', side_effect=fail_second):
                with self.assertRaises(RuntimeError):
                    rollback(run)
            self.assertEqual(fingerprint(), before)
            self.assertFalse(CustomerTenantAuthorization.objects.filter(repair_run_id=run).exists())
            stored = CustomerTenantRepairRun.objects.get(pk=run)
            self.assertFalse(stored.rolled_back)
            self.assertEqual(stored.encrypted_journal, journal)
            self.assertEqual(rollback(run)['restored_links'], 2)

    def test_fingerprint_tracks_explicit_nonpositive_legacy_primary_keys(self):
        before = fingerprint()
        with database_account('app'):
            models.QuerySet(model=VehicleEntry).bulk_create([
                VehicleEntry(pk=-7, tenant=self.a, customer=self.own, plate_number='explicit-legacy-id')
            ])
        self.assertNotEqual(fingerprint(), before)

    def test_definer_view_grant_is_rejected_as_an_indirect_permission_path(self):
        user = settings.CUSTOMER_TENANT_TEST_ACCOUNTS['app']['USER']
        db = guards.identifier(connection.settings_dict['NAME'])
        self.query('CREATE SQL SECURITY DEFINER VIEW guard_auth_view AS SELECT * FROM vehicles_customertenantauthorization')
        self.query(f"GRANT SELECT, INSERT ON {db}.guard_auth_view TO '{user}'@'%'")
        try:
            with self.assertRaises(ImproperlyConfigured):
                guards.install(connection)
            with override_settings(CUSTOMER_TENANT_GUARD_ROLE='application'):
                with database_account('app'):
                    with self.assertRaises(ImproperlyConfigured):
                        self.query('SELECT 1')
        finally:
            self.query(f"REVOKE SELECT, INSERT ON {db}.guard_auth_view FROM '{user}'@'%'")
            self.query('DROP VIEW guard_auth_view')

    def test_audit_rejects_missing_definer_grant_and_retry_repairs_it(self):
        from django.core.management.base import CommandError
        principal = f"'{guards.definer_user(connection.settings_dict['NAME'])}'@'localhost'"
        table = guards.identifier(connection.settings_dict['NAME'])+'.vehicles_customerprofile'
        self.query(f'REVOKE SELECT, TRIGGER ON {table} FROM {principal}')
        try:
            with self.assertRaises(CommandError):
                call_command('check_customer_tenant_guards', stdout=io.StringIO())
        finally:
            guards.install(connection)
        output = io.StringIO()
        call_command('check_customer_tenant_guards', stdout=output)
        self.assertIn('"status": "verified"', output.getvalue())
