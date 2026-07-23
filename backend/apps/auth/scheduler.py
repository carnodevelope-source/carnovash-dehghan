import os
import sys
import threading
import time


_scheduler_started = False
_scheduler_lock = threading.Lock()


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


def _background_jobs_loop():
    from django.db import close_old_connections

    from .nightly_sms import dispatch_due_nightly_manager_summaries
    from .support_tickets import close_stale_support_tickets

    while True:
        try:
            close_old_connections()
            dispatch_due_nightly_manager_summaries()
            close_stale_support_tickets()
            from apps.subscriptions.services import run_expiry_and_reminder_jobs

            run_expiry_and_reminder_jobs()
        except Exception:
            pass
        time.sleep(300)


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
