"""Streaming authenticated encryption; no unencrypted archive is written to disk."""
import base64
import hashlib
import gzip
import io
import json
import os
import re
import stat
import struct
import tarfile
from contextlib import nullcontext
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from django.conf import settings

from .snapshot import SnapshotError, safe_relative

MAGIC = b'CARVASH-BACKUP-1\n'
MAGIC_V2 = b'CARVASH-BACKUP-2\n'
CHUNK = 1024 * 1024


def private_bytes(filename):
    path = Path(filename)
    if path.absolute() != path.resolve():
        raise SnapshotError('invalid_key_file')
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    with os.fdopen(fd, 'rb') as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise SnapshotError('invalid_key_file')
        if os.name == 'posix' and (info.st_mode & 0o077 or info.st_uid not in {0, os.geteuid()}):
            raise SnapshotError('insecure_key_permissions')
        data = source.read(65537)
        if len(data) > 65536:
            raise SnapshotError('invalid_key_file')
        return data.strip()


def key(key_id=None, *, legacy=False):
    key_id = settings.CLOUD_BACKUP_LEGACY_KEY_ID if legacy else (key_id or settings.CLOUD_BACKUP_KEY_ID)
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', key_id):
        raise SnapshotError('invalid_key_id')
    if settings.CLOUD_BACKUP_KEYRING_FILE:
        ring = json.loads(private_bytes(settings.CLOUD_BACKUP_KEYRING_FILE))
        if key_id not in ring:
            raise SnapshotError('unknown_key_id')
        raw = ring[key_id].encode('ascii')
    elif legacy or key_id == settings.CLOUD_BACKUP_KEY_ID:
        raw = private_bytes(settings.CLOUD_BACKUP_KEY_FILE)
    else:
        raise SnapshotError('unknown_key_id')
    value = base64.b64decode(raw, validate=True)
    if len(value) != 32:
        raise SnapshotError('invalid_key')
    return value


def archive_cipher(salt, *, key_id=None, legacy=False):
    derived = HKDF(algorithm=hashes.SHA256(), length=32, salt=salt, info=MAGIC if legacy else MAGIC_V2).derive(key(key_id, legacy=legacy))
    return AESGCM(derived)


class EncryptWriter:
    def __init__(self, output, guard):
        self.output, self.guard = output, guard
        key_id = settings.CLOUD_BACKUP_KEY_ID
        self.key_id = key_id
        self.prefix = os.urandom(32)
        self.cipher = archive_cipher(self.prefix, key_id=key_id)
        encoded_id = key_id.encode('ascii')
        self.aad = MAGIC_V2 + bytes([len(encoded_id)]) + encoded_id + self.prefix
        self.counter = 0
        self.finished = False
        self._write(self.aad)

    def _write(self, data):
        self.guard()
        self.output.write(data)

    def frame(self, data):
        if self.finished or self.counter >= 2 ** 64:
            raise SnapshotError('invalid_writer_state')
        nonce = self.counter.to_bytes(12, 'big')
        encrypted = self.cipher.encrypt(nonce, data, self.aad)
        self._write(struct.pack('>I', len(encrypted)) + encrypted)
        self.counter += 1

    def write(self, data):
        for start in range(0, len(data), CHUNK):
            self.frame(data[start:start + CHUNK])
        return len(data)

    def finish(self):
        self.frame(b'')  # authenticated terminal frame detects truncation
        self.finished = True


class DecryptReader(io.RawIOBase):
    def __init__(self, source):
        self.source = source
        magic = source.read(len(MAGIC))
        if magic not in {MAGIC, MAGIC_V2}:
            raise SnapshotError('invalid_archive')
        key_id = None
        header = magic
        if magic == MAGIC_V2:
            length = source.read(1)
            if len(length) != 1 or not 1 <= length[0] <= 64:
                raise SnapshotError('invalid_key_id')
            encoded_id = source.read(length[0])
            if len(encoded_id) != length[0]:
                raise SnapshotError('truncated_archive')
            key_id = encoded_id.decode('ascii')
            header += length + encoded_id
        self.prefix = source.read(32)
        if len(self.prefix) != 32:
            raise SnapshotError('truncated_archive')
        self.aad = MAGIC if magic == MAGIC else header + self.prefix
        self.cipher, self.counter = archive_cipher(self.prefix, key_id=key_id, legacy=magic == MAGIC), 0
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
            self.buffer = self.cipher.decrypt(nonce, encrypted, self.aad)
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
    with (nullcontext(path) if hasattr(path, 'read') else open(path, 'rb')) as source:
        source.seek(0)
        if output is not None:
            destination = Path(output)
            if destination.is_symlink() or destination.resolve() != destination.absolute() or any(destination.iterdir()):
                raise SnapshotError('unsafe_recovery_directory')
            info = destination.stat()
            if os.name == 'posix' and (info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700):
                raise SnapshotError('unsafe_recovery_directory')
        with io.BufferedReader(DecryptReader(source)) as encrypted_stream, gzip.GzipFile(fileobj=encrypted_stream, mode='rb') as stream:
            with tarfile.open(fileobj=stream, mode='r|') as tar:
                for member in tar:
                    if len(observed) >= settings.CLOUD_BACKUP_MAX_FILES + 2:
                        raise SnapshotError('snapshot_limit_exceeded')
                    name = safe_relative(member.name)
                    if not member.isfile() or name in observed:
                        raise SnapshotError('invalid_member')
                    if name not in {'fixture.json', 'manifest.json'} and not name.startswith('media/'):
                        raise SnapshotError('invalid_member')
                    data = tar.extractfile(member)
                    digest = hashlib.sha256()
                    sink = None
                    captured = bytearray() if name in {'fixture.json', 'manifest.json'} else None
                    if captured is not None and member.size > settings.CLOUD_BACKUP_MAX_JSON_BYTES:
                        raise SnapshotError('snapshot_limit_exceeded')
                    if output is not None:
                        target = Path(output) / name
                        for parent in reversed(target.parent.parents):
                            if parent.is_relative_to(destination) and parent.is_symlink():
                                raise SnapshotError('unsafe_recovery_directory')
                        if target.parent.is_symlink():
                            raise SnapshotError('unsafe_recovery_directory')
                        parent = destination
                        for component in Path(name).parts[:-1]:
                            parent = parent / component
                            if parent.is_symlink():
                                raise SnapshotError('unsafe_recovery_directory')
                            parent.mkdir(mode=0o700, exist_ok=True)
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
            while encrypted_stream.read(CHUNK):
                raise SnapshotError('trailing_data')
    if not manifest or manifest.get('version') != 1 or manifest.get('tenant_id') != tenant_id:
        raise SnapshotError('wrong_tenant')
    observed.pop('manifest.json', None)
    if manifest.get('members') != observed or fixture is None:
        raise SnapshotError('checksum_mismatch')
    validate_fixture(fixture, tenant_id)
    from django.apps import apps
    from django.db.models import FileField
    for item in fixture:
        for field in apps.get_model(item['model'])._meta.fields:
            if isinstance(field, FileField) and (name := item['fields'].get(field.name)):
                if 'media/' + safe_relative(name) not in observed:
                    raise SnapshotError('missing_media_member')
    return manifest


def validate_fixture(fixture, tenant_id):
    from django.apps import apps
    from .snapshot import GLOBAL, CHILDREN, TENANT, ownership_registry
    ownership_registry()
    if not isinstance(fixture, list) or len(fixture) > settings.CLOUD_BACKUP_MAX_ROWS:
        raise SnapshotError('invalid_fixture')
    ids = {(item['model'], item['pk']) for item in fixture}
    if len(ids) != len(fixture) or ('cw_auth.carwash', tenant_id) not in ids:
        raise SnapshotError('invalid_fixture')
    for item in fixture:
        model = apps.get_model(item['model'])
        label, fields = item['model'], item['fields']
        if label not in TENANT | GLOBAL | set(CHILDREN) | {'cw_auth.carwash'}:
            raise SnapshotError('invalid_model')
        if label == 'cw_auth.carwash':
            if item['pk'] != tenant_id:
                raise SnapshotError('wrong_tenant')
        elif label in TENANT:
            if fields.get('tenant') != tenant_id:
                raise SnapshotError('wrong_tenant')
        elif label not in GLOBAL and label not in CHILDREN:
            raise SnapshotError('invalid_model')
        for field in model._meta.fields:
            value = fields.get(field.name)
            if field.is_relation and value is not None:
                if (field.remote_field.model._meta.label_lower, value) not in ids:
                    raise SnapshotError('broken_relation')
        allowed = {f.name for f in model._meta.fields if not f.primary_key}
        if label == 'cw_auth.user':
            allowed |= {'groups', 'user_permissions'}
            if any(fields.get(k) for k in ('is_staff', 'is_superuser', 'platform_role', 'groups', 'user_permissions')):
                raise SnapshotError('unsafe_privileges')
        if set(fields) - allowed:
            raise SnapshotError('invalid_fixture_fields')


def recovery_guard(using):
    from django.db import connections
    if using == 'default' or using not in settings.CLOUD_BACKUP_RECOVERY_ALIASES:
        raise SnapshotError('live_restore_forbidden')
    recovery, live = connections[using].settings_dict, connections['default'].settings_dict
    if recovery['ENGINE'].endswith('sqlite3'):
        left, right = str(recovery['NAME']), str(live['NAME'])
        if left == right or (not left.startswith('file:') and Path(left).resolve() == Path(right).resolve()):
            raise SnapshotError('live_restore_forbidden')
    elif str(recovery['NAME']).casefold() == str(live['NAME']).casefold():
        # Conservative even if host aliases/ports differ: require a distinct name.
        raise SnapshotError('live_restore_forbidden')


def restore_fixture(path, tenant_id, using):
    """Only an explicitly configured recovery DB, never the application's default DB."""
    from django.core import serializers
    from django.db import connections, transaction
    recovery_guard(using)
    fixture = json.loads(Path(path).read_bytes())
    validate_fixture(fixture, tenant_id)
    from django.apps import apps
    from .snapshot import TENANT, CHILDREN
    for label in TENANT | set(CHILDREN) | {'cw_auth.carwash'}:
        if apps.get_model(label).objects.using(using).exists():
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
