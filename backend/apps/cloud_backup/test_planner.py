from datetime import datetime, timedelta
from unittest import TestCase
from zoneinfo import ZoneInfo
from .planner import plan_backup

TEHRAN = ZoneInfo('Asia/Tehran')


class PlannerTests(TestCase):
    def test_ten_day_cycle_no_duplicate_and_inactive(self):
        start = datetime(2026, 10, 27, tzinfo=TEHRAN)
        plan = lambda day, **kw: plan_backup(start + timedelta(days=day), eligible=True,
            last_success=start + timedelta(days=day-1) if day else None,
            last_full=start, chain_healthy=True, **kw)
        self.assertEqual(plan(1).action, 'incremental')
        self.assertEqual(plan(9).action, 'incremental')
        self.assertEqual(plan(10).action, 'full')
        self.assertEqual(plan_backup(start, eligible=True, last_success=start, last_full=start, chain_healthy=True).action, 'skip')
        self.assertEqual(plan_backup(start, eligible=False, last_success=None, last_full=None, chain_healthy=False).action, 'skip')

    def test_missing_or_broken_chain_forces_new_full(self):
        start = datetime(2026, 10, 27, tzinfo=TEHRAN)
        day = start + timedelta(days=2)
        self.assertEqual(plan_backup(day, eligible=True, last_success=start, last_full=start, chain_healthy=True).action, 'full')
        self.assertEqual(plan_backup(day, eligible=True, last_success=day-timedelta(days=1), last_full=start, chain_healthy=False).action, 'full')
        self.assertEqual(plan_backup(day, eligible=True, last_success=None, last_full=None, chain_healthy=False).action, 'full')
