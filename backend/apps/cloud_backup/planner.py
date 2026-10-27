"""Fail-closed per-tenant backup planner; no database or filesystem writes.

Scheduler must invoke this only after validating the complete chain metadata.
Never mark a full snapshot successful until its encrypted archive verifies.
"""
from dataclasses import dataclass
from datetime import timedelta
from .schedule import local_day, backup_kind


@dataclass(frozen=True)
class Plan:
    action: str
    reason: str


def plan_backup(now, *, eligible, last_success, last_full, chain_healthy):
    """Decide a single backup for a tenant at Tehran midnight.

    last_success/last_full are aware datetimes of VERIFIED archives only.
    The caller must enforce locks and durable execution idempotency.
    """
    day = local_day(now)
    if not eligible:
        return Plan('skip', 'subscription_inactive')
    if any(value is not None and local_day(value) > day for value in (last_success, last_full)):
        return Plan('full', 'future_history')
    if last_full is None:
        return Plan('full', 'no_verified_base')
    if not chain_healthy:
        return Plan('full', 'chain_unhealthy')
    if last_success is not None and local_day(last_success) >= day:
        return Plan('skip', 'already_backed_up_today')
    if last_success is None or (day - local_day(last_success)) > timedelta(days=1):
        return Plan('full', 'missing_incremental_day')
    kind = backup_kind(now, last_full)
    return Plan(kind, 'ten_day_full_due' if kind == 'full' else 'daily_incremental')
