"""Streaming authenticated encryption; no unencrypted archive is written to disk."""
import base64
import hashlib
import io
import json
import os
import struct
import tarfile
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from django.conf import settings

from .snapshot import SnapshotError, safe_relative

MAGIC = b'CARVASH-BACKUP-1\n'
CHUNK = 1024 * 1024


def key():
    path = Path(settings.CLOUD_BACKUP_KEY_FILE)
    if os.name == 'posix' and path.stat().st_mode & 0o077:
        raise SnapshotError('insecure_key_permissions')
    raw = path.read_bytes().strip()
    value = base64.b64decode(raw, validate=True)
    if len(value) != 32:
        raise SnapshotError('invalid_key')
    return value


def archive_cipher(salt):
    derived = HKDF(algorithm=hashes.SHA256(), length=32, salt=salt, info=MAGIC).derive(key())
    return AESGCM(derived)


class EncryptWriter:
    def __init__(self, output, guard):
        self.output, self.guard = output, guard
        self.prefix = os.urandom(32)
        self.cipher = archive_cipher(self.prefix)
        self.counter = 0
        self._write(MAGIC + self.prefix)

    def _write(self, data):
        self.guard()
        self.output.write(data)

    def frame(self, data):
        nonce = self.counter.to_bytes(12, 'big')
        encrypted = self.cipher.encrypt(nonce, data, MAGIC)
        self._write(struct.pack('>I', len(encrypted)) + encrypted)
        self.counter += 1

    def write(self, data):
        for start in range(0, len(data), CHUNK):
            self.frame(data[start:start + CHUNK])
        return len(data)

    def finish(self):
        self.frame(b'')  # authenticated terminal frame detects truncation


class DecryptReader(io.RawIOBase):
    def __init__(self, source):
        self.source = source
        if source.read(len(MAGIC)) != MAGIC:
            raise SnapshotError('invalid_archive')
        self.prefix = source.read(32)
        if len(self.prefix) != 32:
            raise SnapshotError('truncated_archive')
        self.cipher, self.counter = archive_cipher(self.prefix), 0
        self.buffer, self.done = b'', False

    def readable(self):
        return True

    def readinto(self, target):
        while not self.buffer and not self.done:
            header = self.source.read(4)
            if len(header) != 4:
                raise SnapshotError('truncated_archive')
            size, = struct.unpack('>I', header)
            if not 16 <= size <= CHUNK + 16:
                raise SnapshotError('invalid_frame')
            encrypted = self.source.read(size)
            if len(encrypted) != size:
                raise SnapshotError('truncated_archive')
            nonce = self.counter.to_bytes(12, 'big')
            self.buffer = self.cipher.decrypt(nonce, encrypted, MAGIC)
            self.counter += 1
            if not self.buffer:
                self.done = True
                if self.source.read(1):
                    raise SnapshotError('trailing_data')
        count = min(len(target), len(self.buffer))
        target[:count], self.buffer = self.buffer[:count], self.buffer[count:]
        return count


def verify(path, tenant_id, output=None):
    """Read every member and authenticated terminal; optionally recover to a NEW directory."""
    observed, manifest, fixture = {}, None, None
    with open(path, 'rb') as source:
        with io.BufferedReader(DecryptReader(source)) as stream:
            with tarfile.open(fileobj=stream, mode='r|gz') as tar:
                for member in tar:
                    name = safe_relative(member.name)
                    if not member.isfile() or name in observed:
                        raise SnapshotError('invalid_member')
                    if name not in {'fixture.json', 'manifest.json'} and not name.startswith('media/'):
                        raise SnapshotError('invalid_member')
                    data = tar.extractfile(member)
                    digest = hashlib.sha256()
                    sink = None
                    captured = bytearray() if name in {'fixture.json', 'manifest.json'} else None
                    if output is not None:
                        target = Path(output) / name
                        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                        sink = open(target, 'xb')
                        os.chmod(target, 0o600)
                    try:
                        while block := data.read(CHUNK):
                            digest.update(block)
                            if captured is not None:
                                captured.extend(block)
                            if sink:
                                sink.write(block)
                    finally:
                        if sink:
                            sink.close()
                    observed[name] = digest.hexdigest()
                    if name == 'manifest.json':
                        manifest = json.loads(captured)
                    elif name == 'fixture.json':
                        fixture = json.loads(captured)
            while stream.read(CHUNK):
                pass
    if not manifest or manifest.get('version') != 1 or manifest.get('tenant_id') != tenant_id:
        raise SnapshotError('wrong_tenant')
    observed.pop('manifest.json', None)
    if manifest.get('members') != observed or fixture is None:
        raise SnapshotError('checksum_mismatch')
    validate_fixture(fixture, tenant_id)
    return manifest


def validate_fixture(fixture, tenant_id):
    from django.apps import apps
    from .snapshot import GLOBAL, CHILDREN, EXCLUDED
    ids = {(item['model'], item['pk']) for item in fixture}
    if len(ids) != len(fixture) or ('cw_auth.carwash', tenant_id) not in ids:
        raise SnapshotError('invalid_fixture')
    for item in fixture:
        model = apps.get_model(item['model'])
        label, fields = item['model'], item['fields']
        if label in EXCLUDED or model._meta.app_label in {'cloud_backup', 'realtime', 'auth', 'sessions'}:
            raise SnapshotError('invalid_model')
        if label == 'cw_auth.carwash':
            if item['pk'] != tenant_id:
                raise SnapshotError('wrong_tenant')
        elif 'tenant' in {f.name for f in model._meta.fields}:
            if fields.get('tenant') != tenant_id:
                raise SnapshotError('wrong_tenant')
        elif label not in GLOBAL and label not in CHILDREN:
            raise SnapshotError('invalid_model')
        for field in model._meta.fields:
            value = fields.get(field.name)
            if field.is_relation and value is not None:
                if (field.remote_field.model._meta.label_lower, value) not in ids:
                    raise SnapshotError('broken_relation')


def restore_fixture(path, tenant_id, using):
    """Only an explicitly configured recovery DB, never the application's default DB."""
    from django.core import serializers
    from django.db import connections, transaction
    from apps.auth.models import CarWash
    recovery = connections[using].settings_dict
    live = connections['default'].settings_dict
    if using == 'default' or all(recovery.get(k) == live.get(k) for k in ('ENGINE', 'HOST', 'PORT', 'NAME')):
        raise SnapshotError('live_restore_forbidden')
    fixture = json.loads(Path(path).read_bytes())
    validate_fixture(fixture, tenant_id)
    if CarWash.objects.using(using).exists():
        raise SnapshotError('recovery_database_not_empty')
    connection = connections[using]
    with connection.constraint_checks_disabled():
        with transaction.atomic(using=using):
            for item in fixture:
                from django.apps import apps
                model = apps.get_model(item['model'])
                existing = model.objects.using(using).filter(pk=item['pk']).first()
                if existing:
                    # Shared catalogs may already exist after migrations; never overwrite them.
                    from .snapshot import GLOBAL
                    saved = json.loads(serializers.serialize('json', [existing]))[0]
                    if item['model'] not in GLOBAL or saved != item:
                        raise SnapshotError('recovery_collision')
                    continue
                obj = next(serializers.deserialize('json', json.dumps([item])))
                obj.save(using=using)
            connection.check_constraints()
            from django.core.management.color import no_style
            from django.apps import apps
            models = list({apps.get_model(item['model']) for item in fixture})
            with connection.cursor() as cursor:
                for sql in connection.ops.sequence_reset_sql(no_style(), models):
                    cursor.execute(sql)
