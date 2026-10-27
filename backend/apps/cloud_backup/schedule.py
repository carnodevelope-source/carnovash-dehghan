"""Deterministic Tehran-midnight planning for future incremental chains.

This module does not start backup jobs or claim incremental support.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

TEHRAN = ZoneInfo('Asia/Tehran')
FULL_EVERY_DAYS = 10
RETENTION_DAYS = 30


def local_day(moment):
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError('An aware timestamp is required')
    return moment.astimezone(TEHRAN).date()


def midnight_utc(day):
    return datetime.combine(day, datetime.min.time(), tzinfo=TEHRAN).astimezone(timezone.utc)


def next_midnight(moment):
    return midnight_utc(local_day(moment) + timedelta(days=1))


def backup_kind(moment, chain_start):
    """First snapshot and each tenth Tehran calendar day must be a full snapshot.

    Caller must independently ensure the full chain exists and is verified.
    """
    if chain_start is None:
        return 'full'
    elapsed = (local_day(moment) - local_day(chain_start)).days
    if elapsed < 0:
        raise ValueError('Chain start is in the future')
    return 'full' if elapsed >= FULL_EVERY_DAYS else 'incremental'


def retained_chain_indices(chains, now):
    """Select entire chains intersecting the 30-day window.

    Each chain is a sequence of (timestamp, archive_id) entries with a full
    archive first. Never return an isolated delta. Actual deletion requires
    separate successful recovery verification and an active eligible tenant.
    """
    cutoff = local_day(now) - timedelta(days=RETENTION_DAYS)
    retained = []
    for index, chain in enumerate(chains):
        if not chain:
            continue
        days = [local_day(timestamp) for timestamp, _ in chain]
        if days != sorted(days):
            raise ValueError('Chain entries must be chronological')
        if days[-1] >= cutoff:
            retained.append(index)
    return retained
