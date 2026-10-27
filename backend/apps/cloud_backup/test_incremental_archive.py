import base64
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest import TestCase
from django.test import override_settings
from .incremental_archive import create_delta_archive, read_delta_archive, reconstruct_delta
from .media_delta import diff_media
from .delta import diff_fixture
from .snapshot import SnapshotError
import hashlib


def sha(b):
    return hashlib.sha256(b).hexdigest()


def row(pk, name):
    return {'model': 'vehicles.vehicleentry', 'pk': pk, 'fields': {'tenant': 3, 'name': name}}


class EncryptedIncrementalArchiveTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.key = self.root / 'key'
        self.key.write_bytes(base64.b64encode(os.urandom(32)))
        self.key.chmod(0o600)
        self.config = override_settings(CLOUD_BACKUP_KEY_FILE=str(self.key), CLOUD_BACKUP_KEY_ID='primary')
        self.config.enable()
        self.addCleanup(self.config.disable)
        self.media = self.root / 'media'
        self.media.mkdir()

    @contextmanager
    def open_file(self, name):
        with open(self.media / name, 'rb') as file:
            yield file

    def test_encrypted_delta_restore_and_tamper_detection(self):
        previous = [row(1, 'old'), row(2, 'deleted')]
        current = [row(1, 'updated'), row(3, 'new')]
        old_media = {'old.jpg': sha(b'deleted'), 'edit.jpg': sha(b'old'), 'same.jpg': sha(b'same')}
        new_media = {'edit.jpg': sha(b'new'), 'same.jpg': sha(b'same'), 'add.jpg': sha(b'added')}
        for name, content in {'edit.jpg': b'new', 'same.jpg': b'same', 'add.jpg': b'added'}.items():
            (self.media / name).write_bytes(content)
        archive = self.root / 'delta.cvb'
        create_delta_archive(archive, 3, previous, current, old_media, new_media, self.open_file)
        self.assertNotIn(b'updated', archive.read_bytes())
        self.assertNotIn(b'added', archive.read_bytes())
        output = self.root / 'staging'
        output.mkdir(mode=0o700)
        metadata = read_delta_archive(archive, 3, output)
        recovered, recovered_media = reconstruct_delta(previous, old_media, metadata)
        self.assertEqual(recovered, current)
        self.assertEqual(recovered_media, new_media)
        self.assertEqual((output / 'media/edit.jpg').read_bytes(), b'new')
        self.assertEqual((output / 'media/add.jpg').read_bytes(), b'added')
        self.assertFalse((output / 'media/same.jpg').exists())
        self.assertFalse((output / 'media/old.jpg').exists())
        with self.assertRaises(SnapshotError):
            read_delta_archive(archive, 4, self.root / 'wrong')
        data = bytearray(archive.read_bytes())
        data[len(data) // 2] ^= 1
        archive.write_bytes(data)
        another = self.root / 'tamper'
        another.mkdir(mode=0o700)
        with self.assertRaises(Exception):
            read_delta_archive(archive, 3, another)
