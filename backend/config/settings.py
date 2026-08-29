import socket
from pathlib import Path
from decouple import config
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def _csv_config(name, default=''):
    return [item.strip() for item in config(name, default=default).split(',') if item.strip()]


def _local_dev_origins():
    if not DEBUG:
        return []

    ports = _csv_config('DJANGO_DEV_FRONTEND_PORTS', default='5173')
    addresses = set()
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            address = info[4][0]
            if address and not address.startswith('127.'):
                addresses.add(address)
    except OSError:
        pass

    return [f'http://{address}:{port}' for address in sorted(addresses) for port in ports]

SECRET_KEY = config('DJANGO_SECRET_KEY', default='replace-me')
DEBUG = config('DJANGO_DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = list(
    dict.fromkeys(
        [
            *[host.strip() for host in config('DJANGO_ALLOWED_HOSTS', default='*').split(',') if host.strip()],
            'localhost',
            '127.0.0.1',
            'backend',
        ]
    )
)
if not DEBUG and SECRET_KEY == 'replace-me':
    raise ImproperlyConfigured('DJANGO_SECRET_KEY must be set in production.')
if not DEBUG and ('*' in ALLOWED_HOSTS or not ALLOWED_HOSTS):
    raise ImproperlyConfigured('DJANGO_ALLOWED_HOSTS must be explicitly set in production.')
PLATE_AI_SERVICE_URL = config('PLATE_AI_SERVICE_URL', default='http://127.0.0.1:8765')
PLATE_AI_TIMEOUT_SECONDS = config('PLATE_AI_TIMEOUT_SECONDS', default=5.0, cast=float)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'apps.auth.apps.AuthConfig',
    'apps.vehicles.apps.VehiclesConfig',
    'apps.services.apps.ServicesConfig',
    'apps.workers.apps.WorkersConfig',
    'apps.payments.apps.PaymentsConfig',
    'apps.products.apps.ProductsConfig',
    'apps.reports',
    'apps.notifications.apps.NotificationsConfig',
    'apps.inventory.apps.InventoryConfig',
    'apps.subscriptions.apps.SubscriptionsConfig',
    'apps.realtime.apps.RealtimeConfig',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'apps.realtime.request_id.RequestIdMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # Must run after authentication: replay entries are scoped to user/tenant.
    'apps.realtime.idempotency.IdempotencyMiddleware',
    'apps.auth.middleware.TenantLicenseLockMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

DB_ENGINE = config('DB_ENGINE', default='mysql')
DB_SQL_MODE = config(
    'DB_SQL_MODE',
    default='STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION',
)
if DB_ENGINE == 'sqlite':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': config('DB_SQLITE_NAME', default=str(BASE_DIR / 'db.sqlite3')),
        }
    }
else:
    # XAMPP ships MariaDB 10.4; Django 5.1+ stock backend requires 10.5+.
    DATABASES = {
        'default': {
            'ENGINE': config('DB_BACKEND', default='config.db.mysql'),
            'NAME': config('DB_NAME', default='carwash'),
            'USER': config('DB_USER', default='root'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='127.0.0.1'),
            'PORT': config('DB_PORT', default='3306'),
            'OPTIONS': {
                'charset': 'utf8mb4',
                # Strict mode is set per application connection as well as by
                # Docker's server option, so every Django worker has the same
                # data-integrity behavior.
                'init_command': f"SET SESSION sql_mode = '{DB_SQL_MODE}'",
            },
            # Reusing connections removes a MySQL handshake from every request.
            'CONN_MAX_AGE': config('DB_CONN_MAX_AGE', default=60, cast=int),
            'CONN_HEALTH_CHECKS': True,
        }
    }

REDIS_URL = config('REDIS_URL', default='')

# Upper bound on concurrent /api/live/events/ streams per worker process; each
# one holds a server thread until its browser tab goes away.
LIVE_MAX_SUBSCRIBERS = config('LIVE_MAX_SUBSCRIBERS', default=12, cast=int)
# Shared channel that lets an event raised in one worker process reach streams
# attached to the others. Empty means single-process delivery only.
LIVE_REDIS_URL = config('LIVE_REDIS_URL', default=REDIS_URL)
LIVE_REDIS_CHANNEL = config('LIVE_REDIS_CHANNEL', default='carvash:live')
# V2 is shipped dark. Enable each stage only after staging/soak evidence has
# been recorded; Redis/SSE remains a signal and MySQL remains authoritative.
LIVE_V2_ENABLED = config('LIVE_V2_ENABLED', default=False, cast=bool)
LIVE_REPLAY_ENABLED = config('LIVE_REPLAY_ENABLED', default=False, cast=bool)
LIVE_OUTBOX_ENABLED = config('LIVE_OUTBOX_ENABLED', default=False, cast=bool)
LIVE_ASGI_ENABLED = config('LIVE_ASGI_ENABLED', default=False, cast=bool)
LIVE_REVISION_SAFETY_CHECK = config('LIVE_REVISION_SAFETY_CHECK', default=True, cast=bool)
LIVE_OUTBOX_RETENTION_HOURS = config('LIVE_OUTBOX_RETENTION_HOURS', default=72, cast=int)
LIVE_REPLAY_BATCH_SIZE = config('LIVE_REPLAY_BATCH_SIZE', default=100, cast=int)
LIVE_REPLAY_MAX_EVENTS = config('LIVE_REPLAY_MAX_EVENTS', default=1000, cast=int)
LIVE_REPLAY_MAX_AGE_HOURS = config('LIVE_REPLAY_MAX_AGE_HOURS', default=72, cast=int)
LIVE_OUTBOX_CLEANUP_BATCH_SIZE = config('LIVE_OUTBOX_CLEANUP_BATCH_SIZE', default=500, cast=int)
LIVE_OUTBOX_CLEANUP_MAX_BATCHES = config('LIVE_OUTBOX_CLEANUP_MAX_BATCHES', default=20, cast=int)
LIVE_REDIS_CONNECT_TIMEOUT_SECONDS = config('LIVE_REDIS_CONNECT_TIMEOUT_SECONDS', default=2.0, cast=float)
LIVE_REDIS_SOCKET_TIMEOUT_SECONDS = config('LIVE_REDIS_SOCKET_TIMEOUT_SECONDS', default=2.0, cast=float)
IDEMPOTENCY_ENABLED = config('IDEMPOTENCY_ENABLED', default=True, cast=bool)
IDEMPOTENCY_RETENTION_HOURS = config('IDEMPOTENCY_RETENTION_HOURS', default=168, cast=int)
IDEMPOTENCY_CLEANUP_BATCH_SIZE = config('IDEMPOTENCY_CLEANUP_BATCH_SIZE', default=500, cast=int)
IDEMPOTENCY_CLEANUP_MAX_BATCHES = config('IDEMPOTENCY_CLEANUP_MAX_BATCHES', default=20, cast=int)

if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
            'KEY_PREFIX': 'carvash',
        }
    }
    # cached_db keeps the database as the source of truth, so an eviction or a
    # Redis restart costs a lookup rather than logging everyone out.
    SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

SESSION_COOKIE_AGE = config('DJANGO_SESSION_COOKIE_AGE', default=60 * 60 * 24 * 14, cast=int)
SESSION_SAVE_EVERY_REQUEST = False

AUTH_USER_MODEL = 'cw_auth.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fa-ir'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = config('DJANGO_STATIC_ROOT', default=str(BASE_DIR / 'staticfiles'))
MEDIA_URL = '/media/'
MEDIA_ROOT = config('DJANGO_MEDIA_ROOT', default=str(BASE_DIR / 'media'))
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

USE_X_FORWARDED_HOST = config('DJANGO_USE_X_FORWARDED_HOST', default=not DEBUG, cast=bool)
SESSION_COOKIE_SECURE = config('DJANGO_SESSION_COOKIE_SECURE', default=not DEBUG, cast=bool)
CSRF_COOKIE_SECURE = config('DJANGO_CSRF_COOKIE_SECURE', default=not DEBUG, cast=bool)
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SAMESITE = config('DJANGO_SESSION_COOKIE_SAMESITE', default='Lax')
CSRF_COOKIE_SAMESITE = config('DJANGO_CSRF_COOKIE_SAMESITE', default='Lax')
SECURE_SSL_REDIRECT = config('DJANGO_SECURE_SSL_REDIRECT', default=not DEBUG, cast=bool)
SECURE_REDIRECT_EXEMPT = [r'^api/health/$']
if config('DJANGO_SECURE_PROXY_SSL_HEADER', default=not DEBUG, cast=bool):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = config('DJANGO_SECURE_REFERRER_POLICY', default='same-origin')
SECURE_HSTS_SECONDS = config('DJANGO_SECURE_HSTS_SECONDS', default=(3600 if not DEBUG else 0), cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config('DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS', default=not DEBUG, cast=bool)
SECURE_HSTS_PRELOAD = config('DJANGO_SECURE_HSTS_PRELOAD', default=False, cast=bool)

CORS_ALLOW_ALL_ORIGINS = False
DEFAULT_DEV_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    *_local_dev_origins(),
]
CORS_ALLOWED_ORIGINS = _csv_config(
    'DJANGO_CORS_ALLOWED_ORIGINS',
    default=','.join(DEFAULT_DEV_ORIGINS),
)
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = _csv_config(
    'DJANGO_CSRF_TRUSTED_ORIGINS',
    default=','.join(CORS_ALLOWED_ORIGINS),
)

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'EXCEPTION_HANDLER': 'config.api.exception_handler',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'login': config('DJANGO_THROTTLE_LOGIN', default='10/minute'),
        'tenant_register': config('DJANGO_THROTTLE_TENANT_REGISTER', default='5/hour'),
        'attendance_public': config('DJANGO_THROTTLE_ATTENDANCE_PUBLIC', default='30/minute'),
        'csrf': config('DJANGO_THROTTLE_CSRF', default='60/minute'),
    },
}

IRANPAYAMAK_BASE_URL = config('IRANPAYAMAK_BASE_URL', default='https://api.iranpayamak.com')
IRANPAYAMAK_API_KEY = config('IRANPAYAMAK_API_KEY', default='')
IRANPAYAMAK_LINE_NUMBER = config('IRANPAYAMAK_LINE_NUMBER', default='')
SMS_PRICE_PER_SEGMENT = config('SMS_PRICE_PER_SEGMENT', default=185, cast=int)
SMS_CHARS_PER_SEGMENT = config('SMS_CHARS_PER_SEGMENT', default=70, cast=int)
# IranPayamak appends unsubscribe text; counted in billable length (empty to disable).
SMS_PROVIDER_FOOTER = config('SMS_PROVIDER_FOOTER', default='\nلغو11')
# Keep vehicle assign/release SMS off the request path so operator actions stay snappy.
SMS_SEND_IN_BACKGROUND = config('SMS_SEND_IN_BACKGROUND', default=True, cast=bool)
