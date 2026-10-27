"""Explicit, encrypted and atomic maintenance of historical customer links.

Only this module uses an unprotected QuerySet, to restore the exact legacy state
on an approved rollback. Operational code must use the protected managers.
"""
import hashlib
import json
import os
import re

from cryptography.fernet import Fernet, InvalidToken
from django.core.management.base import CommandError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models, transaction

from .models import CustomerProfile, CustomerTenantRepairRun, VehicleEntry
from .loyalty import rebuild_customer_score


def codec():
    try:
        return Fernet(os.environ['CUSTOMER_REPAIR_KEY'].encode('ascii'))
    except (KeyError, ValueError, UnicodeError):
        raise CommandError('Set CUSTOMER_REPAIR_KEY to a dedicated Fernet key.') from None


def encode(value):
    return json.dumps(value, cls=DjangoJSONEncoder, sort_keys=True, separators=(',', ':')).encode()


def digest(value):
    return hashlib.sha256(encode(value)).hexdigest()


def seal(value):
    return codec().encrypt(encode(value)).decode('ascii')


def unseal(value):
    try:
        return json.loads(codec().decrypt(value.encode('ascii')))
    except (InvalidToken, ValueError, UnicodeError):
        raise CommandError('Invalid encrypted repair artifact or key.') from None


def state(lock=False):
    # Deliberately conservative: any change to customers or visits invalidates
    # approval/rollback. Run during a maintenance window for large databases.
    if lock:
        from apps.auth.models import CarWash
        # Lock parent rows first: MySQL FK checks block new child inserts while
        # the approval snapshot is checked and applied. Lock all tenants because
        # this conservative snapshot includes all customer and vehicle rows.
        list(CarWash.objects.order_by('pk').select_for_update().values_list('pk', flat=True))
    customers = CustomerProfile.objects.order_by('pk')
    vehicles = VehicleEntry.objects.order_by('pk')
    if lock:
        customers = customers.select_for_update()
        vehicles = vehicles.select_for_update()
    return {'customers': list(customers.values()), 'vehicles': list(vehicles.values())}


def normalized_phone(value):
    value = (value or '').strip().translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789'))
    if value.startswith('+98'):
        value = '0' + value[3:]
    elif value.startswith('0098'):
        value = '0' + value[4:]
    return value if re.fullmatch(r'09[0-9]{9}', value) else None


def make_plan(tenant=None):
    snapshot = state()
    customers = {c['id']: c for c in snapshot['customers']}
    index = {}
    for c in customers.values():
        phone = normalized_phone(c['phone'])
        if phone:
            index.setdefault((c['tenant_id'], phone), []).append(c['id'])
    actions = []
    proposed = set()
    for v in snapshot['vehicles']:
        if tenant is not None and v['tenant_id'] != tenant:
            continue
        c = customers.get(v['customer_id'])
        if not c or (v['tenant_id'] is not None and v['tenant_id'] == c['tenant_id']):
            continue
        phone = normalized_phone(v['driver_phone'])
        matches = index.get((v['tenant_id'], phone), []) if phone else []
        kind = 'unrepairable' if not phone or v['tenant_id'] is None else 'ambiguous' if len(matches) > 1 else 'link' if matches else 'create'
        if kind == 'create':
            proposed.add((v['tenant_id'], phone))
        actions.append({'vehicle': v['id'], 'old_customer': v['customer_id'], 'tenant': v['tenant_id'],
                        'phone': phone, 'target': matches[0] if len(matches) == 1 else None, 'kind': kind})
    return {'version': 1, 'tenant': tenant, 'state_hash': digest(snapshot), 'actions': actions,
            'summary': {'mismatches': len(actions), 'repairable': sum(a['kind'] in ('link', 'create') for a in actions),
                        'ambiguous': sum(a['kind'] == 'ambiguous' for a in actions),
                        'unrepairable': sum(a['kind'] == 'unrepairable' for a in actions),
                        'proposed_profiles': len(proposed)}}


def write_plan(path, plan):
    # Exclusive creation prevents accidental overwrite; no plaintext temp file.
    encrypted = seal(plan)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='ascii') as stream:
        stream.write(encrypted)


def apply_plan(plan, approved_hash):
    if digest(plan) != approved_hash or plan.get('version') != 1:
        raise CommandError('Plan approval hash does not match.')
    with transaction.atomic():
        before = state(lock=True)
        if digest(before) != plan['state_hash']:
            raise CommandError('Database changed since planning; generate and review a new plan.')
        if make_plan(plan.get('tenant')) != plan:
            raise CommandError('Plan contents do not match current repair proposals.')
        actionable = [a for a in plan['actions'] if a['kind'] in ('create', 'link')]
        created = []
        affected = set()
        changes = []
        for action in actionable:
            vehicle = VehicleEntry.objects.get(pk=action['vehicle'])
            if vehicle.tenant_id != action['tenant'] or vehicle.customer_id != action['old_customer'] or normalized_phone(vehicle.driver_phone) != action['phone']:
                raise CommandError('Plan action no longer matches the database.')
            target = action['target']
            if target:
                customer = CustomerProfile.objects.get(pk=target, tenant_id=vehicle.tenant_id)
                if normalized_phone(customer.phone) != action['phone']:
                    raise CommandError('Plan target no longer matches.')
            else:
                customer, new = CustomerProfile.objects.get_or_create(tenant_id=vehicle.tenant_id, phone=action['phone'])
                if new:
                    created.append(customer.pk)
            affected.update((vehicle.customer_id, customer.pk))
            # No save/signals: do not send SMS, mutate payment or plate snapshots.
            models.QuerySet(model=VehicleEntry, using='default').filter(pk=vehicle.pk).update(customer_id=customer.pk)
            changes.append({'vehicle': vehicle.pk, 'old': vehicle.customer_id, 'new': customer.pk})
        for customer in CustomerProfile.objects.filter(pk__in=affected).order_by('pk'):
            rebuild_customer_score(customer)
        journal = {'before': before, 'after_hash': digest(state()), 'changes': changes,
                   'created': created, 'affected': sorted(affected)}
        run = CustomerTenantRepairRun.objects.create(plan_hash=approved_hash, encrypted_journal=seal(journal))
        return run.pk, len(changes)


def rollback(run_id):
    with transaction.atomic():
        run = CustomerTenantRepairRun.objects.select_for_update().get(pk=run_id)
        if run.rolled_back:
            raise CommandError('Repair was already rolled back.')
        journal = unseal(run.encrypted_journal)
        if digest(state(lock=True)) != journal['after_hash']:
            raise CommandError('Database changed since repair; rollback refused.')
        for change in journal['changes']:
            models.QuerySet(model=VehicleEntry, using='default').filter(pk=change['vehicle']).update(customer_id=change['old'])
        originals = {c['id']: c for c in journal['before']['customers']}
        for pk in journal['affected']:
            if pk in originals:
                c = originals[pk]
                CustomerProfile.objects.filter(pk=pk).update(yearly_score=c['yearly_score'], score_year=c['score_year'], updated_at=c['updated_at'])
        CustomerProfile.objects.filter(pk__in=journal['created']).delete()
        run.rolled_back = True
        run.save(update_fields=['rolled_back'])
