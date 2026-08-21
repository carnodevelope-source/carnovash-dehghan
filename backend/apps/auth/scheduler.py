import os
import sys
import threading
import time
import uuid


_scheduler_started = False
_scheduler_lock = threading.Lock()

CYCLE_SECONDS = 300
# Shorter than the cycle so the next tick can always re-acquire, but long enough
# that a slow cycle never lets a second worker start the same jobs.
LOCK_TTL_SECONDS = 280
LOCK_KEY = 'carvash:scheduler:background-jobs'

_instance_token = uuid.uuid4().hex


def _should_start_scheduler():
    if os.environ.get('CARWASH_INTERNAL_SCHEDULER', '').strip().lower() in {'1', 'true', 'yes', 'on'}:
        return True
    command = ' '.join(sys.argv[1:]).lower()
    if 'runserver' not in command:
        return False
    run_main = os.environ.get('RUN_MAIN')
    if run_main and run_main != 'true':
        return False
    return True


def _acquire_cycle_lease():
    """Elect a single runner per cycle so multi-worker deployments don't duplicate jobs."""
    from django.conf import settings

    redis_url = getattr(settings, 'REDIS_URL', '')
    if not redis_url:
        # Single process (runserver); there is nobody to race with.
        return True
    try:
        import redis

        client = redis.Redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
        return bool(client.set(LOCK_KEY, _instance_token, nx=True, ex=LOCK_TTL_SECONDS))
    except Exception:
        # Never let a Redis hiccup silently stop nightly SMS and expiry jobs.
        return True


def _background_jobs_loop():
    from django.db import close_old_connections

    from .nightly_sms import dispatch_due_nightly_manager_summaries
    from .support_tickets import close_stale_support_tickets

    while True:
        try:
            close_old_connections()
            if _acquire_cycle_lease():
                dispatch_due_nightly_manager_summaries()
                close_stale_support_tickets()
                from apps.subscriptions.services import run_expiry_and_reminder_jobs

                run_expiry_and_reminder_jobs()
        except Exception:
            pass
        finally:
            close_old_connections()
        time.sleep(CYCLE_SECONDS)


def start_internal_scheduler():
    global _scheduler_started
    if not _should_start_scheduler():
        return
    with _scheduler_lock:
        if _scheduler_started:
            return
        worker = threading.Thread(target=_background_jobs_loop, name='auth-background-jobs-loop', daemon=True)
        worker.start()
        _scheduler_started = True
