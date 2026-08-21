import os


def _int_env(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(minimum, int(os.environ.get(name) or default))
    except (TypeError, ValueError):
        return default


bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:8000')

# /api/live/events/ streams hold their handler open for the lifetime of the tab.
# Sync workers would let a handful of browser tabs occupy every worker process
# and stall all other requests, so requests must be served on threads instead.
worker_class = 'gthread'
workers = _int_env('GUNICORN_WORKERS', 3)
threads = _int_env('GUNICORN_THREADS', 24)

timeout = _int_env('GUNICORN_TIMEOUT', 120)
graceful_timeout = _int_env('GUNICORN_GRACEFUL_TIMEOUT', 30)
keepalive = _int_env('GUNICORN_KEEPALIVE', 5)

accesslog = os.environ.get('GUNICORN_ACCESS_LOG', '-')
errorlog = os.environ.get('GUNICORN_ERROR_LOG', '-')
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')
