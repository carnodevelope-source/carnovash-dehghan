"""Real child-process death/restart; all paths and DBs belong to tests."""
import json
import os
import selectors
import signal
import subprocess
import sys
import textwrap
from unittest import skipUnless
from django.db import connection
from django.test import TransactionTestCase
from .tests import CloudBackupTests
from .models import BackupRun
from .staging import private_staging, cleanup_staging


class ProcessRecoveryTests(TransactionTestCase):
    databases = CloudBackupTests.databases
    setUp = CloudBackupTests.setUp
    archive = CloudBackupTests.archive

    def child(self, code):
        process = subprocess.Popen([sys.executable, '-u', '-c', textwrap.dedent(code)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: process.kill() if process.poll() is None else None)
        return process

    def ready(self, process):
        selector = selectors.DefaultSelector()
        try:
            selector.register(process.stdout, selectors.EVENT_READ)
            self.assertTrue(selector.select(15), 'child failed to reach checkpoint')
            line = process.stdout.readline().strip()
            self.assertTrue(line.startswith('READY '), line)
            return line[6:]
        finally:
            selector.close()

    def test_real_sigkill_reaps_plaintext_without_tenant_subscription(self):
        process = self.child(f"""
import os, time
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apps.cloud_backup.test_settings')
import django
django.setup()
from apps.cloud_backup.staging import private_staging
with private_staging({self.a.pk}) as stage:
    (stage / 'plaintext').write_bytes(b'isolated test fixture')
    print('READY ' + str(stage), flush=True)
    time.sleep(120)
""")
        from pathlib import Path
        stage = Path(self.ready(process))
        self.assertEqual(cleanup_staging(), 0, 'Reaper removed active worker staging')
        process.kill()
        process.wait(timeout=10)
        self.assertEqual(process.returncode, -signal.SIGKILL)
        self.assertTrue(stage.exists())
        self.assertGreaterEqual(cleanup_staging(), 1)
        self.assertFalse(stage.exists())

    @skipUnless(connection.vendor == 'mysql', 'Cross-process durable history requires isolated MySQL')
    def test_real_worker_kill_and_new_process_restart_preserves_history(self):
        database = connection.settings_dict['NAME']
        self.assertTrue(database.startswith('test_'), 'Refusing non-test DB')
        config = {'database': database, 'disk': str(self.disk), 'media': str(self.media),
                  'key': str(self.key), 'tenant': self.a.pk}
        code = """
import os,json,time
os.environ.setdefault('DJANGO_SETTINGS_MODULE','apps.cloud_backup.test_settings_mysql')
from django.conf import settings
config=CONFIG
settings.DATABASES['default']['NAME']=config['database']
import django
django.setup()
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from django.test import override_settings
from apps.cloud_backup import service
from apps.cloud_backup.scheduled_chain import execute_tenant
@contextmanager
def pin():
    yield Path(config['disk'])
original=service.verify
def checkpoint(*args,**kwargs):
    result=original(*args,**kwargs)
    print('READY verified-partial',flush=True)
    time.sleep(120)
    return result
with override_settings(CLOUD_BACKUP_MOUNT=config['disk'],CLOUD_BACKUP_ROOT=config['disk'],
        MEDIA_ROOT=config['media'],CLOUD_BACKUP_KEY_FILE=config['key'],CLOUD_BACKUP_MIN_FREE_BYTES=0), \
        patch.object(service,'mount_guard'), patch.object(service,'pinned_root',pin):
    if KILL_CHECKPOINT:
        with patch.object(service,'verify',checkpoint):
            execute_tenant(config['tenant'])
    else:
        run=execute_tenant(config['tenant'])
        print('RESTART '+run.status,flush=True)
""".replace('CONFIG', repr(config))
        process = self.child(code.replace('KILL_CHECKPOINT', 'True'))
        self.ready(process)
        self.assertEqual(BackupRun.objects.filter(tenant_id=self.a.pk, status='running').count(), 1)
        self.assertFalse(BackupRun.objects.filter(status='success').exists())
        process.kill()
        process.wait(timeout=10)
        self.assertTrue(list(self.disk.rglob('*.partial')))
        restarted = self.child(code.replace('KILL_CHECKPOINT', 'False'))
        output, errors = restarted.communicate(timeout=30)
        self.assertEqual(restarted.returncode, 0, errors)
        self.assertIn('RESTART success', output)
        self.assertEqual(BackupRun.objects.filter(status='success').count(), 1)
        self.assertEqual(BackupRun.objects.filter(error_code='worker_interrupted').count(), 1)
        self.assertFalse(list(self.disk.rglob('*.partial')))
