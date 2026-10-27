"""Approved, encrypted maintenance; deliberate raw writes are confined here.

MySQL guards enforce ordinary writes; only a separate, restricted maintenance
account can issue an exact, one-use rollback authorization.
"""
import hashlib
from datetime import datetime
from contextlib import contextmanager
import json
import os
import re

from cryptography.fernet import Fernet, InvalidToken
from django.core.management.base import CommandError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection, models, transaction
from django.db.models import F, Q
from django.utils import timezone

from .models import CustomerProfile, CustomerTenantRepairRun, VehicleEntry
from .loyalty import rebuild_customer_score

BATCH_SIZE = 500
PLAN_VERSION = 2


def codec():
    try:
        return Fernet(os.environ['CUSTOMER_REPAIR_KEY'].encode('ascii'))
    except (KeyError, ValueError, UnicodeError):
        raise CommandError('Set CUSTOMER_REPAIR_KEY to a dedicated Fernet key.') from None


class ExactJSONEncoder(DjangoJSONEncoder):
    def default(self, value):
        if isinstance(value, datetime):
            return value.isoformat(timespec='microseconds')
        return super().default(value)


def encode(value):
    return json.dumps(value, cls=ExactJSONEncoder, sort_keys=True, separators=(',', ':')).encode()


def digest(value):
    return hashlib.sha256(encode(value)).hexdigest()


def seal(value):
    return codec().encrypt(encode(value)).decode('ascii')


def unseal(value):
    try:
        return json.loads(codec().decrypt(value.encode('ascii')))
    except (InvalidToken, ValueError, UnicodeError):
        raise CommandError('Invalid encrypted repair artifact or key.') from None


def rows(model, *, lock=False, fields=None):
    """Keyset pages bound MySQL client buffering as well as Python allocation."""
    last = None
    while True:
        query = model.objects.order_by('pk')
        if last is not None:
            query = query.filter(pk__gt=last)
        if lock:
            query = query.select_for_update()
        if lock and connection.vendor == 'mysql':
            # MySQL FOR UPDATE requires write privileges even for tables that
            # maintenance must never modify. FOR SHARE locks rows and RR gaps
            # with SELECT alone. Django has no shared-lock QuerySet API.
            def shared_read(execute, sql, params, many, context):
                suffix = 'FOR UPDATE'
                if not sql.endswith(suffix):
                    raise CommandError('Unexpected locking SQL; maintenance aborted.')
                return execute(sql[:-len(suffix)] + 'FOR SHARE', params, many, context)
            with connection.execute_wrapper(shared_read):
                page = list(query.values(*(fields or []))[:BATCH_SIZE])
        else:
            page = list(query.values(*(fields or []))[:BATCH_SIZE])
        if not page:
            return
        yield from page
        last = page[-1][model._meta.pk.attname]


def tracked_models():
    from django.apps import apps
    # Include financial and loyalty/history data even if not changed by repair.
    labels = (
        'cw_auth.CarWash', 'vehicles.CustomerProfile', 'vehicles.VehicleEntry',
        'vehicles.PlateLoyaltyProfile', 'vehicles.VehicleJob',
        'vehicles.VehicleJobService', 'vehicles.VehicleJobProduct',
        'vehicles.VehicleStatusLog', 'payments.Wallet', 'payments.Payment',
        'payments.CashflowTransaction', 'payments.WalletGatewayRequest',
    )
    return [apps.get_model(label) for label in labels]


def fingerprint(*, lock=False):
    hasher = hashlib.sha256()
    # Parent rows first. On MySQL parent FK locks block new related inserts.
    for model in tracked_models():
        hasher.update(encode(model._meta.label_lower) + b'\n')
        for row in rows(model, lock=lock):
            hasher.update(encode(row) + b'\n')
    return hasher.hexdigest()


def state(lock=False):
    """Test/audit helper only; planning, apply and rollback never materialize this."""
    if lock:
        fingerprint(lock=True)
    return {'customers': list(rows(CustomerProfile)), 'vehicles': list(rows(VehicleEntry))}


def normalized_phone(value):
    value = (value or '').strip().translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789'))
    if value.startswith('+98'):
        value = '0' + value[3:]
    elif value.startswith('0098'):
        value = '0' + value[4:]
    return value if re.fullmatch(r'09[0-9]{9}', value) else None


def build_plan(tenant, state_hash):
    invalid = VehicleEntry.objects.filter(customer__isnull=False).filter(
        Q(tenant_id__isnull=True) | Q(customer__tenant_id__isnull=True)
        | ~Q(tenant_id=F('customer__tenant_id'))
    )
    if tenant is not None:
        invalid = invalid.filter(tenant_id=tenant)
    # Only mismatches and matching phones occupy memory, not every visit/profile.
    actions = []
    last = None
    while True:
        query = invalid if last is None else invalid.filter(pk__gt=last)
        page = list(query.order_by('pk').values(
            'id', 'customer_id', 'tenant_id', 'driver_phone',
        )[:BATCH_SIZE])
        if not page:
            break
        for v in page:
            phone = normalized_phone(v['driver_phone'])
            actions.append({'vehicle': v['id'], 'old_customer': v['customer_id'],
                            'tenant': v['tenant_id'], 'phone': phone})
        last = page[-1]['id']
    wanted = {(a['tenant'], a['phone']) for a in actions if a['phone'] and a['tenant'] is not None}
    index = {}
    if wanted:
        for c in rows(CustomerProfile, fields=['id', 'tenant_id', 'phone']):
            key = (c['tenant_id'], normalized_phone(c['phone']))
            if key in wanted:
                index.setdefault(key, []).append(c['id'])
    proposed = set()
    for action in actions:
        key = (action['tenant'], action['phone'])
        matches = index.get(key, [])
        if (not action['phone'] or action['tenant'] is None or action['vehicle'] < 0
                or action['old_customer'] < 0 or any(pk < 0 for pk in matches)):
            # Authorization IDs are unsigned. Preserve anomalous historical IDs
            # for human review rather than proposing a non-reversible repair.
            kind = 'unrepairable'
        elif len(matches) > 1:
            kind = 'ambiguous'
        else:
            kind = 'link' if matches else 'create'
        if kind == 'create':
            proposed.add(key)
        action.update(kind=kind, target=matches[0] if len(matches) == 1 else None)
    return {'version': PLAN_VERSION, 'tenant': tenant, 'state_hash': state_hash, 'actions': actions,
            'summary': {'mismatches': len(actions),
                        'repairable': sum(a['kind'] in ('link', 'create') for a in actions),
                        'ambiguous': sum(a['kind'] == 'ambiguous' for a in actions),
                        'unrepairable': sum(a['kind'] == 'unrepairable' for a in actions),
                        'proposed_profiles': len(proposed)}}


def make_plan(tenant=None):
    before = fingerprint()
    plan = build_plan(tenant, before)
    if fingerprint() != before:
        raise CommandError('Database changed during planning; stop writers and retry.')
    return plan


def write_plan(path, plan):
    encrypted = seal(plan)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='ascii') as stream:
        stream.write(encrypted)


def score_state(customer):
    return {key: getattr(customer, key) for key in ('yearly_score', 'score_year', 'updated_at')}


@contextmanager
def repair_transaction():
    # Django defaults MySQL to READ COMMITTED, whose locking scans do not lock
    # gaps. Use next-transaction RR so the paged full-range locking reads also
    # block new rows with NULL FKs and new tenants. Do not mutate session defaults.
    if connection.vendor != 'mysql':
        with transaction.atomic():
            yield
        return
    if connection.in_atomic_block or not connection.get_autocommit():
        raise CommandError('Repair requires an outermost transaction on MySQL.')
    lock_name = 'cw_customer_repair_' + hashlib.sha256(connection.settings_dict['NAME'].encode()).hexdigest()[:32]
    with connection.cursor() as cursor:
        cursor.execute('SELECT GET_LOCK(%s, 10)', [lock_name])
        if cursor.fetchone()[0] != 1:
            raise CommandError('Another maintenance transaction is active.')
    try:
        with connection.cursor() as cursor:
            cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        with transaction.atomic():
            yield
    finally:
        with connection.cursor() as cursor:
            cursor.execute('SELECT RELEASE_LOCK(%s)', [lock_name])



def apply_plan(plan, approved_hash):
    if digest(plan) != approved_hash or plan.get('version') != PLAN_VERSION:
        raise CommandError('Plan approval hash/version does not match; regenerate old plans.')
    from .mysql_guards import require_maintenance
    require_maintenance(connection)
    with repair_transaction():
        before_hash = fingerprint(lock=True)
        if CustomerTenantRepairRun.objects.filter(plan_hash=approved_hash).exists():
            raise CommandError('Plan was already applied; replay refused.')
        if before_hash != plan['state_hash']:
            raise CommandError('Database changed since planning; generate and review a new plan.')
        if build_plan(plan.get('tenant'), before_hash) != plan:
            raise CommandError('Plan contents do not match current repair proposals.')
        created, affected, changes = [], set(), []
        actionable = [a for a in plan['actions'] if a['kind'] in ('create', 'link')]
        old_ids = {a['old_customer'] for a in actionable} | {a['target'] for a in actionable if a['target'] is not None}
        originals = {str(c.pk): score_state(c) for c in CustomerProfile.objects.filter(pk__in=old_ids)}
        for action in actionable:
            vehicle = VehicleEntry.objects.get(pk=action['vehicle'])
            if action['target'] is not None:
                customer = CustomerProfile.objects.get(pk=action['target'], tenant_id=vehicle.tenant_id)
            else:
                customer, new = CustomerProfile.objects.get_or_create(tenant_id=vehicle.tenant_id, phone=action['phone'])
                if new:
                    created.append(customer.pk)
            affected.update((vehicle.customer_id, customer.pk))
            # Deliberately bypass save/signals: no payment, SMS or plate mutation.
            models.QuerySet(model=VehicleEntry, using='default').filter(pk=vehicle.pk).update(customer_id=customer.pk)
            changes.append({'vehicle': vehicle.pk, 'old': vehicle.customer_id, 'new': customer.pk})
        for customer in CustomerProfile.objects.filter(pk__in=affected).order_by('pk'):
            rebuild_customer_score(customer)
        journal = {'version': 2, 'original_scores': originals, 'after_hash': fingerprint(),
                   'changes': changes, 'created': created, 'affected': sorted(affected)}
        run = CustomerTenantRepairRun.objects.create(plan_hash=approved_hash, encrypted_journal=seal(journal))
        return run.pk, len(changes)


def rollback(run_id):
    from .mysql_guards import require_maintenance
    require_maintenance(connection)
    with repair_transaction():
        # Same lock ordering as apply to minimize deadlocks between operators.
        current_hash = fingerprint(lock=True)
        run = CustomerTenantRepairRun.objects.select_for_update().get(pk=run_id)
        if run.rolled_back:
            raise CommandError('Repair was already rolled back.')
        journal = unseal(run.encrypted_journal)
        if journal.get('version') != 2:
            # v1 did not fingerprint payments/history: cannot safely attest that
            # no business activity occurred. Preserve the journal for review.
            raise CommandError('Legacy journal cannot prove unchanged financial/history data; manual review required.')
        if current_hash != journal['after_hash']:
            raise CommandError('Database changed since repair; rollback refused.')
        for change in journal['changes']:
            authorize_rollback(run, change)
            models.QuerySet(model=VehicleEntry, using='default').filter(pk=change['vehicle']).update(customer_id=change['old'])
        for pk, original in journal['original_scores'].items():
            CustomerProfile.objects.filter(pk=pk).update(**original)
        # Retain every created profile, including identity, score and timestamps.
        # The restored links may leave profiles unreferenced; report, never delete.
        unreferenced = list(CustomerProfile.objects.filter(pk__in=journal['created'], vehicle_entries__isnull=True)
                            .order_by('pk').values_list('pk', flat=True))
        report = {'restored_links': len(journal['changes']), 'retained_customers': journal['created'],
                  'unreferenced_customers': unreferenced}
        journal['rollback'] = dict(report, completed_at=timezone.now().isoformat())
        run.encrypted_journal = seal(journal)
        run.rolled_back = True
        run.save(update_fields=['rolled_back', 'encrypted_journal'])
        return report


def authorize_rollback(run, change):
    """Issue only after decryption, state/version/approval checks under locks."""
    if connection.vendor != 'mysql' or change['old'] is None:
        return
    from .models import CustomerTenantAuthorization
    vehicle = VehicleEntry.objects.get(pk=change['vehicle'])
    old = CustomerProfile.objects.get(pk=change['old'])
    if vehicle.tenant_id is not None and vehicle.tenant_id == old.tenant_id:
        return  # Ordinary valid transition needs no exceptional permission.
    if vehicle.customer_id != change['new']:
        raise CommandError('Rollback transition changed; authorization refused.')
    with connection.cursor() as cursor:
        cursor.execute('SELECT CONNECTION_ID(), UTC_TIMESTAMP(6)')
        connection_id, now = cursor.fetchone()
    from datetime import timedelta, timezone as datetime_timezone
    CustomerTenantAuthorization.objects.create(
        connection_id=connection_id, vehicle_id=vehicle.pk, tenant_id=vehicle.tenant_id,
        from_customer_id=vehicle.customer_id, to_customer_id=old.pk,
        repair_run_id=run.pk, plan_hash=run.plan_hash,
        expires_at=now.replace(tzinfo=datetime_timezone.utc) + timedelta(minutes=5),
    )
