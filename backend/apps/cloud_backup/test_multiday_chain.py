"""Disposable encrypted full + multi-day incremental integration tests."""
import base64
import hashlib
import json
import os
import tarfile
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest import TestCase
from django.test import override_settings
from .archive import EncryptWriter
from .snapshot import add_bytes, SnapshotError
from .incremental_archive import create_delta_archive
from .chain_recovery import recover_chain


def digest(data):
    return hashlib.sha256(data).hexdigest()


class MultiDayChainTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        key = self.root / 'key'
        key.write_bytes(base64.b64encode(os.urandom(32)))
        key.chmod(0o600)
        config = override_settings(CLOUD_BACKUP_KEY_FILE=str(key), CLOUD_BACKUP_KEY_ID='primary')
        config.enable()
        self.addCleanup(config.disable)
        self.media_root = self.root / 'sources'
        self.media_root.mkdir()
        self.base = self.root / 'full.cvb'
        self.full_fixture = [{'model': 'cw_auth.carwash', 'pk': 3, 'fields': {'name': 'Original'}}]
        with self.base.open('wb') as output:
            writer = EncryptWriter(output, lambda: None)
            data = json.dumps(self.full_fixture).encode()
            members = {'fixture.json': digest(data)}
            with tarfile.open(fileobj=writer, mode='w|gz') as tar:
                add_bytes(tar, 'fixture.json', data)
                add_bytes(tar, 'manifest.json', json.dumps({'version': 1, 'tenant_id': 3, 'members': members}).encode())
            writer.finish()

    @contextmanager
    def open_media(self, name):
        with (self.media_root / name).open('rb') as stream:
            yield stream

    def test_three_day_chain_and_missing_link_fail_closed(self):
        previous, previous_media = self.full_fixture, {}
        deltas = []
        for day in range(1, 4):
            fixture = [{'model': 'cw_auth.carwash', 'pk': 3, 'fields': {'name': f'Day {day}'}}]
            name = f'photo-{day}.jpg'
            (self.media_root / name).write_bytes(f'PHOTO {day}'.encode())
            current_media = {name: digest(f'PHOTO {day}'.encode())}
            path = self.root / f'day-{day}.cvb'
            create_delta_archive(path, 3, previous, fixture, previous_media, current_media, self.open_media)
            deltas.append(path)
            previous, previous_media = fixture, current_media
        result = self.root / 'result'
        self.assertEqual(recover_chain(self.base, deltas, 3, result), previous)
        self.assertEqual((result / 'media/photo-3.jpg').read_bytes(), b'PHOTO 3')
        self.assertFalse((result / 'media/photo-1.jpg').exists())
        self.assertFalse((result / 'media/photo-2.jpg').exists())
        broken = self.root / 'missing-middle'
        with self.assertRaises(ValueError):
            recover_chain(self.base, [deltas[0], deltas[2]], 3, broken)
        self.assertFalse(broken.exists())
        wrong = self.root / 'wrong-tenant'
        with self.assertRaises(SnapshotError):
            recover_chain(self.base, deltas, 4, wrong)
        self.assertFalse(wrong.exists())
