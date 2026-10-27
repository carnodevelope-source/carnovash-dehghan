"""Test-only privileged legacy fixtures and real restricted-account execution."""
from contextlib import contextmanager
from datetime import timedelta, timezone

from django.conf import settings
from django.core.management import call_command as django_call_command
from django.db import connections, models

from apps.vehicles.models import CustomerTenantAuthorization, VehicleEntry


@contextmanager
def database_account(role, alias='default'):
    connection = connections[alias]
    if connection.vendor != 'mysql':
        yield
        return
    if connection.in_atomic_block:
        raise RuntimeError('Account tests require TransactionTestCase.')
    previous = connection.settings_dict
    connection.close()
    connection.settings_dict = dict(previous, **settings.CUSTOMER_TENANT_TEST_ACCOUNTS[role])
    try:
        yield
    finally:
        connection.close()
        connection.settings_dict = previous


def apply_plan(*args, **kwargs):
    from apps.vehicles.customer_tenant_repair import apply_plan as implementation
    with database_account('maint'):
        return implementation(*args, **kwargs)


def rollback(*args, **kwargs):
    from apps.vehicles.customer_tenant_repair import rollback as implementation
    with database_account('maint'):
        return implementation(*args, **kwargs)


def call_command(name, *args, **kwargs):
    if name == 'repair_customer_tenant_links' and (kwargs.get('apply') or kwargs.get('rollback') is not None):
        with database_account('maint'):
            return django_call_command(name, *args, **kwargs)
    return django_call_command(name, *args, **kwargs)


def restore_legacy_link(vehicle, customer):
    connection = connections['default']
    if connection.vendor == 'mysql':
        with connection.cursor() as cursor:
            cursor.execute('SELECT CONNECTION_ID(), UTC_TIMESTAMP(6)')
            cid, now = cursor.fetchone()
        CustomerTenantAuthorization.objects.create(
            connection_id=cid, vehicle_id=vehicle.pk, tenant_id=vehicle.tenant_id,
            from_customer_id=vehicle.customer_id, to_customer_id=customer.pk,
            repair_run_id=0, plan_hash='0' * 64,
            expires_at=now.replace(tzinfo=timezone.utc) + timedelta(minutes=5),
        )
    models.QuerySet(model=VehicleEntry).filter(pk=vehicle.pk).update(customer_id=customer.pk)
    vehicle.customer_id = customer.pk


def seed_legacy_vehicles(vehicles):
    for vehicle in vehicles:
        foreign = vehicle.customer
        vehicle.customer = None
        models.QuerySet(model=VehicleEntry).bulk_create([vehicle])
        if vehicle.pk is None:
            with connections['default'].cursor() as cursor:
                cursor.execute('SELECT LAST_INSERT_ID()')
                vehicle.pk = cursor.fetchone()[0]
        restore_legacy_link(vehicle, foreign)
