"""Optional ASGI Gunicorn configuration; WSGI remains the default path."""

import os


def _int_env(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(minimum, int(os.environ.get(name) or default))
    except (TypeError, ValueError):
        return default


bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:8000')
worker_class = 'uvicorn_worker.GunicornWorker'
workers = _int_env('ASGI_WORKERS', _int_env('GUNICORN_WORKERS', 3))
timeout = _int_env('GUNICORN_TIMEOUT', 120)
graceful_timeout = _int_env('GUNICORN_GRACEFUL_TIMEOUT', 30)
keepalive = _int_env('GUNICORN_KEEPALIVE', 5)
max_requests = _int_env('GUNICORN_MAX_REQUESTS', 0, minimum=0)
max_requests_jitter = _int_env('GUNICORN_MAX_REQUESTS_JITTER', 0, minimum=0)
accesslog = os.environ.get('GUNICORN_ACCESS_LOG', '-')
errorlog = os.environ.get('GUNICORN_ERROR_LOG', '-')
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')
