"""Tenant-scoped logical snapshot. Unknown relations fail closed, never expand to other tenants."""
import io
import json
import re
from pathlib import Path, PurePosixPath

from django.apps import apps
from django.conf import settings
from django.core import serializers
from django.db import models

from apps.auth.models import CarWash


class SnapshotError(Exception):
    pass


GLOBAL = {'subscriptions.platformproject', 'subscriptions.serviceproduct', 'subscriptions.serviceplan'}
CHILDREN = {
    'cw_auth.supportticketmessage': 'ticket__tenant_id',
    'cw_auth.supportticketattachment': 'ticket__tenant_id',
    'subscriptions.serviceperiod': 'subscription__tenant_id',
    'subscriptions.serviceusagemeter': 'subscription__tenant_id',
}
EXCLUDED = {'subscriptions.bulkservicejob', 'subscriptions.bulkservicejobitem'}


def safe_relative(name):
    path = PurePosixPath(name)
    if not name or path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:
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


def collect(tenant_id):
    selected = {CarWash._meta.label_lower: [CarWash.objects.get(pk=tenant_id)]}
    for model in apps.get_models():
        label = model._meta.label_lower
        if not model._meta.app_config.name.startswith('apps.') or label in EXCLUDED:
            continue
        if model._meta.app_label in {'cloud_backup', 'realtime'} or model is CarWash:
            continue
        names = {f.name for f in model._meta.fields}
        if 'tenant' in names:
            selected[label] = list(model.objects.filter(tenant_id=tenant_id).order_by('pk'))
        elif label in CHILDREN:
            selected[label] = list(model.objects.filter(**{CHILDREN[label]: tenant_id}).order_by('pk'))
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
                            bucket.append(target.objects.get(pk=pk))
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
                if field.is_relation:
                    pk = getattr(obj, field.attname)
                    label = field.remote_field.model._meta.label_lower
                    if pk is not None and pk not in ids.get(label, set()):
                        # HQ authors are references only. Cross-tenant references are errors.
                        external = field.remote_field.model.objects.filter(pk=pk).first()
                        is_hq = label == 'cw_auth.user' and external and external.tenant_id is None
                        if field.null and is_hq:
                            setattr(obj, field.attname, None)
                        else:
                            raise SnapshotError('foreign_tenant_relation')

    objects = [obj for label in sorted(selected) for obj in selected[label]]
    fixture = json.loads(serializers.serialize('json', objects))
    # Do not restore platform privileges/group membership through tenant archives.
    for item in fixture:
        if item['model'] == 'cw_auth.user':
            item['fields'].update(is_staff=False, is_superuser=False, platform_role='', groups=[], user_permissions=[])
    audit_root = Path(settings.MEDIA_ROOT) / 'ai_plate_audit'
    if audit_root.exists():
        for sidecar in audit_root.rglob('*.json'):
            if not sidecar.is_file() or sidecar.is_symlink():
                raise SnapshotError('unsafe_media')
            # Daily jsonl files mix tenants and must never be copied wholesale.
            sidecar = media_path(sidecar.relative_to(Path(settings.MEDIA_ROOT)).as_posix())
            record = json.loads(sidecar.read_text(encoding='utf-8'))
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
    return json.dumps(fixture, ensure_ascii=False).encode(), sorted(files)


def add_bytes(tar, name, data):
    import tarfile
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = 0o600
    tar.addfile(info, io.BytesIO(data))
