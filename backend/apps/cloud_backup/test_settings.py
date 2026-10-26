from config.settings import *  # noqa: F403

DATABASES = {
    'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'},
    'recovery': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': 'recovery-test.sqlite3'},
}
CLOUD_BACKUP_RECOVERY_ALIASES = ['recovery']
