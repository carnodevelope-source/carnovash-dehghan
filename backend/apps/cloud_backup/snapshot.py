"""Tenant-scoped logical snapshot. Unknown relations fail closed, never expand to other tenants."""
import io
import hashlib
import json
import os
import re
import stat
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

from django.apps import apps
from django.conf import settings
from django.core import serializers
from django.db import models

from apps.auth.models import CarWash


class SnapshotError(Exception):
    def __init__(self, code, *, diagnostics=None):
        super().__init__(code)
        self.diagnostics = diagnostics or {}


class StoredBytes(models.Func):
    function = 'OCTET_LENGTH'
    output_field = models.IntegerField()

    def as_sqlite(self, compiler, connection, **extra_context):
        return super().as_sql(compiler, connection, template='LENGTH(CAST(%(expressions)s AS BLOB))', **extra_context)


def limit_error(metric, observed, limit, *, model=None):
    # Only schema labels and aggregate sizes/counts, never values, SQL or PII.
    detail = {'metric': metric, 'observed': int(observed), 'limit': int(limit)}
    if model is not None:
        detail['model'] = model._meta.label_lower
    return SnapshotError('snapshot_limit_exceeded', diagnostics=detail)


class MediaFiles(list):
    """Paths plus identity captured during the database snapshot."""
    def __init__(self, names, fingerprints, digests):
        super().__init__(names)
        self.fingerprints, self.digests = fingerprints, digests


def fingerprint(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


@contextmanager
def open_media(name):
    path = media_path(name)
    if os.name != 'posix':
        with open(path, 'rb') as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise SnapshotError('unsafe_media')
            yield source
        return
    # Walk every component relative to a pinned directory, never follow links.
    fd = os.open(settings.MEDIA_ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        parts = PurePosixPath(name).parts
        for component in parts[:-1]:
            next_fd = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        file_fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        with os.fdopen(file_fd, 'rb') as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise SnapshotError('unsafe_media')
            yield source
    finally:
        os.close(fd)


GLOBAL = {'subscriptions.platformproject', 'subscriptions.serviceproduct', 'subscriptions.serviceplan'}
CHILDREN = {
    'cw_auth.supportticketmessage': 'ticket__tenant_id',
    'cw_auth.supportticketattachment': 'ticket__tenant_id',
    'subscriptions.serviceperiod': 'subscription__tenant_id',
    'subscriptions.serviceusagemeter': 'subscription__tenant_id',
}
EXCLUDED = {'subscriptions.bulkservicejob', 'subscriptions.bulkservicejobitem'}
TENANT = set('''
cw_auth.user cw_auth.carwashfeaturepurchase cw_auth.supportticket cw_auth.pendingtenantregistration
vehicles.customerprofile vehicles.plateloyaltyprofile vehicles.vehicleentry vehicles.blockedplate
vehicles.vehiclestatuslog vehicles.vehiclejob vehicles.vehiclejobservice vehicles.vehiclejobproduct
services.servicecategory services.service services.servicechangelog services.generalsettings
workers.workerprofile workers.workerattendance payments.wallet payments.payment
payments.cashflowtransaction payments.walletgatewayrequest products.productcategory products.product
reports.reportsnapshot reports.workerpayouttransaction notifications.notificationlog
notifications.smstemplate notifications.customergroup notifications.importedcustomer
inventory.inventoryitem inventory.stockmovement inventory.expenseentry
subscriptions.servicesubscription subscriptions.serviceorder subscriptions.servicepaymentrecord
subscriptions.serviceauditlog subscriptions.servicealert
'''.split())
TECHNICAL = {'realtime.liveoutbox', 'realtime.idempotencyrecord', 'cloud_backup.backuprun'}


def ownership_registry():
    registry = {'cw_auth.carwash': 'root'}
    registry.update({label: 'tenant' for label in TENANT})
    registry.update({label: 'child' for label in CHILDREN})
    registry.update({label: 'global' for label in GLOBAL})
    registry.update({label: 'excluded' for label in EXCLUDED | TECHNICAL})
    for model in apps.get_models():
        if model._meta.app_config.name.startswith('apps.'):
            if model._meta.label_lower not in registry:
                raise SnapshotError('unclassified_model')
            if model._meta.label_lower in TENANT and 'tenant' not in {f.name for f in model._meta.fields}:
                raise SnapshotError('invalid_ownership')
            if model._meta.many_to_many and model._meta.label_lower != 'cw_auth.user':
                raise SnapshotError('unclassified_m2m')
    return registry


def safe_relative(name):
    path = PurePosixPath(name)
    if not name or path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name or path.as_posix() != name or '\x00' in name or path.as_posix() == '.':
        raise SnapshotError('unsafe_path')
    return path.as_posix()


def media_path(name):
    name = safe_relative(name)
    root = Path(settings.MEDIA_ROOT).resolve()
    path = root / name
    # Reject symlinks including intermediate directories.
    for parent in [path, *path.parents]:
        if parent == root:
            break
        if parent.is_symlink():
            raise SnapshotError('unsafe_media')
    if not path.resolve().is_relative_to(root):
        raise SnapshotError('unsafe_media')
    return path


def serialize_row(obj):
    # Do not query or export platform auth-group/permission membership.
    fields = [f.name for f in obj._meta.fields if not f.primary_key]
    return serializers.serialize('json', [obj], fields=fields)


def collect(tenant_id):
    ownership_registry()
    used_rows, used_bytes = 0, 0

    def bounded(query):
        nonlocal used_rows, used_bytes
        count = query.count() + used_rows
        if count > settings.CLOUD_BACKUP_MAX_ROWS:
            raise limit_error('rows', count, settings.CLOUD_BACKUP_MAX_ROWS, model=query.model)
        # Avoid fetching an arbitrarily large DB field into worker memory.
        from django.db.models.functions import Cast
        for field in query.model._meta.fields:
            if isinstance(field, (models.TextField, models.CharField, models.JSONField)):
                measured = query.annotate(_backup_length=StoredBytes(Cast(field.name, models.TextField())))
                limit = min(settings.CLOUD_BACKUP_MAX_FIELD_BYTES, settings.CLOUD_BACKUP_MAX_JSON_BYTES)
                if measured.filter(_backup_length__gt=limit).exists():
                    from django.db.models import Max
                    size = measured.aggregate(size=Max('_backup_length'))['size']
                    raise limit_error('field_length', size, limit, model=query.model)
        rows = []
        for obj in query.iterator(chunk_size=100):
            used_rows += 1
            used_bytes += len(serialize_row(obj).encode())
            if used_rows > settings.CLOUD_BACKUP_MAX_ROWS:
                raise limit_error('rows', used_rows, settings.CLOUD_BACKUP_MAX_ROWS, model=query.model)
            if used_bytes > settings.CLOUD_BACKUP_MAX_JSON_BYTES:
                raise limit_error('fixture_bytes', used_bytes, settings.CLOUD_BACKUP_MAX_JSON_BYTES, model=query.model)
            rows.append(obj)
        return rows

    selected = {CarWash._meta.label_lower: bounded(CarWash.objects.filter(pk=tenant_id))}
    for model in apps.get_models():
        label = model._meta.label_lower
        if not model._meta.app_config.name.startswith('apps.') or label in EXCLUDED:
            continue
        if model._meta.app_label in {'cloud_backup', 'realtime'} or model is CarWash:
            continue
        if label in TENANT:
            query = model.objects.filter(tenant_id=tenant_id).order_by('pk')
            if label == 'cw_auth.user':
                # HQ support is a platform identity even if historically assigned
                # to a tenant. Never export that account's private profile.
                query = query.exclude(platform_role='hq_support')
            selected[label] = bounded(query)
        elif label in CHILDREN:
            selected[label] = bounded(model.objects.filter(**{CHILDREN[label]: tenant_id}).order_by('pk'))
        elif label not in GLOBAL:
            raise SnapshotError('unclassified_model')

    # Include only referenced shared catalog rows, never arbitrary reverse relations.
    changed = True
    while changed:
        changed = False
        for rows in list(selected.values()):
            for obj in rows:
                for field in obj._meta.fields:
                    if not field.is_relation:
                        continue
                    target = field.remote_field.model
                    label = target._meta.label_lower
                    pk = getattr(obj, field.attname)
                    if pk is not None and label in GLOBAL:
                        bucket = selected.setdefault(label, [])
                        if pk not in {item.pk for item in bucket}:
                            bucket.extend(bounded(target.objects.filter(pk=pk)))
                            changed = True

    ids = {label: {obj.pk for obj in rows} for label, rows in selected.items()}
    files = set()
    for rows in selected.values():
        for obj in rows:
            for field in obj._meta.fields:
                if isinstance(field, models.FileField):
                    name = str(getattr(obj, field.name) or '')
                    if name:
                        safe_relative(name)
                        # Check all FileFields, including references through a
                        # different model, before trusting ownership of a path.
                        for owner_model in apps.get_models():
                            for owner_field in owner_model._meta.fields:
                                if not isinstance(owner_field, models.FileField):
                                    continue
                                owners = owner_model.objects.filter(**{owner_field.name: name})
                                if 'tenant' in {f.name for f in owner_model._meta.fields}:
                                    others = owners.exclude(tenant_id=tenant_id)
                                elif owner_model._meta.label_lower in CHILDREN:
                                    others = owners.exclude(**{CHILDREN[owner_model._meta.label_lower]: tenant_id})
                                elif owners.exists():
                                    raise SnapshotError('unowned_file')
                                else:
                                    continue
                                if others.exists():
                                    raise SnapshotError('shared_media')
                        files.add(name)
                        if len(files) > settings.CLOUD_BACKUP_MAX_FILES:
                            raise limit_error('files', len(files), settings.CLOUD_BACKUP_MAX_FILES)
                if field.is_relation:
                    pk = getattr(obj, field.attname)
                    label = field.remote_field.model._meta.label_lower
                    if pk is not None and pk not in ids.get(label, set()):
                        # HQ authors are references only. Cross-tenant references are errors.
                        external = field.remote_field.model.objects.filter(pk=pk).first()
                        is_hq = label == 'cw_auth.user' and external and (
                            external.tenant_id is None or external.platform_role == 'hq_support'
                        )
                        if field.null and is_hq:
                            setattr(obj, field.attname, None)
                        else:
                            raise SnapshotError('foreign_tenant_relation')

    objects = [obj for label in sorted(selected) for obj in selected[label]]
    fixture = [json.loads(serialize_row(obj))[0] for obj in objects]
    # Do not restore platform privileges/group membership through tenant archives.
    for item in fixture:
        if item['model'] == 'cw_auth.user':
            item['fields'].update(is_staff=False, is_superuser=False, platform_role='', groups=[], user_permissions=[])
    fingerprints, digests = {}, {}
    audit_root = Path(settings.MEDIA_ROOT) / 'ai_plate_audit'
    if audit_root.exists():
        for sidecar in audit_root.rglob('*.json'):
            # Vehicle PKs are global. Avoid opening other tenants' audit JSON.
            match = re.fullmatch(r'vehicle-(\d+)-.*\.json', sidecar.name)
            if not match or int(match[1]) not in ids.get('vehicles.vehicleentry', set()):
                continue
            if not sidecar.is_file() or sidecar.is_symlink():
                raise SnapshotError('unsafe_media')
            # Daily jsonl files mix tenants and must never be copied wholesale.
            sidecar = media_path(sidecar.relative_to(Path(settings.MEDIA_ROOT)).as_posix())
            relative_sidecar = sidecar.relative_to(Path(settings.MEDIA_ROOT)).as_posix()
            with open_media(relative_sidecar) as source:
                info = os.fstat(source.fileno())
                if info.st_size > settings.CLOUD_BACKUP_MAX_FIELD_BYTES:
                    raise limit_error('sidecar_bytes', info.st_size, settings.CLOUD_BACKUP_MAX_FIELD_BYTES)
                raw = source.read(settings.CLOUD_BACKUP_MAX_FIELD_BYTES + 1)
                if fingerprint(info) != fingerprint(os.fstat(source.fileno())) or len(raw) > settings.CLOUD_BACKUP_MAX_FIELD_BYTES:
                    raise SnapshotError('source_changed')
                record = json.loads(raw)
            if record.get('tenant_id') != tenant_id:
                continue
            image = safe_relative(record.get('image_path', ''))
            if record.get('vehicle_id') not in ids.get('vehicles.vehicleentry', set()):
                raise SnapshotError('unowned_audit')
            if not re.fullmatch(rf'vehicle-{record["vehicle_id"]}-.*', PurePosixPath(image).name):
                raise SnapshotError('unsafe_audit')
            if media_path(image).with_suffix('.json') != sidecar:
                raise SnapshotError('unsafe_audit')
            files.update({image, sidecar.relative_to(Path(settings.MEDIA_ROOT)).as_posix()})
            fingerprints[relative_sidecar] = fingerprint(info)
            digests[relative_sidecar] = hashlib.sha256(raw).hexdigest()
            if len(files) > settings.CLOUD_BACKUP_MAX_FILES:
                raise limit_error('files', len(files), settings.CLOUD_BACKUP_MAX_FILES)
    payload = json.dumps(fixture, ensure_ascii=False).encode()
    if len(payload) > settings.CLOUD_BACKUP_MAX_JSON_BYTES:
        raise limit_error('fixture_bytes', len(payload), settings.CLOUD_BACKUP_MAX_JSON_BYTES)
    for name in files:
        with open_media(name) as source:
            captured = fingerprint(os.fstat(source.fileno()))
            if name in fingerprints and fingerprints[name] != captured:
                raise SnapshotError('source_changed')
            fingerprints[name] = captured
    return payload, MediaFiles(sorted(files), fingerprints, digests)


def add_bytes(tar, name, data):
    import tarfile
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = 0o600
    tar.addfile(info, io.BytesIO(data))
