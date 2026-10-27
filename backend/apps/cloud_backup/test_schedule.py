"""No database or production service required for schedule validation."""
from datetime import datetime, timedelta, timezone
from unittest import TestCase
from zoneinfo import ZoneInfo
from .schedule import backup_kind, local_day, midnight_utc, next_midnight, retained_chain_indices

UTC = timezone.utc
TEHRAN = ZoneInfo('Asia/Tehran')


class MidnightScheduleTests(TestCase):
    def test_next_midnight_uses_tehran_not_host_timezone(self):
        instant = datetime(2026, 10, 27, 20, 29, tzinfo=UTC)
        self.assertEqual(next_midnight(instant), datetime(2026, 10, 27, 20, 30, tzinfo=UTC))
        self.assertEqual(next_midnight(instant + timedelta(minutes=2)), datetime(2026, 10, 28, 20, 30, tzinfo=UTC))

    def test_full_every_tenth_local_day(self):
        start = datetime(2026, 10, 27, tzinfo=TEHRAN)
        self.assertEqual(backup_kind(start, None), 'full')
        for offset in range(1, 10):
            self.assertEqual(backup_kind(start + timedelta(days=offset), start), 'incremental')
        self.assertEqual(backup_kind(start + timedelta(days=10), start), 'full')

    def test_invalid_timestamps_fail_closed(self):
        with self.assertRaises(ValueError):
            local_day(datetime(2026, 10, 27))
        with self.assertRaises(ValueError):
            backup_kind(datetime(2026, 10, 26, tzinfo=UTC), datetime(2026, 10, 27, tzinfo=UTC))

    def test_retention_never_orphans_delta(self):
        now = datetime(2026, 11, 30, tzinfo=TEHRAN)
        old = [(datetime(2026, 10, 1, tzinfo=TEHRAN), 'full'), (datetime(2026, 10, 2, tzinfo=TEHRAN), 'delta')]
        crossing = [(datetime(2026, 10, 25, tzinfo=TEHRAN), 'full'), (datetime(2026, 11, 1, tzinfo=TEHRAN), 'delta')]
        fresh = [(datetime(2026, 11, 25, tzinfo=TEHRAN), 'full')]
        self.assertEqual(retained_chain_indices([old, crossing, fresh], now), [1, 2])

    def test_midnight_round_trip(self):
        local = datetime(2027, 1, 1, tzinfo=TEHRAN)
        self.assertEqual(midnight_utc(local.date()).astimezone(TEHRAN), local)
