from config.settings import *  # noqa: F403
import tempfile

_test_media = tempfile.TemporaryDirectory(prefix='carvash-backup-test-media-')
MEDIA_ROOT = _test_media.name

DATABASES = {
    'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'},
    'recovery': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': 'recovery-test.sqlite3'},
}
CLOUD_BACKUP_RECOVERY_ALIASES = ['recovery']
