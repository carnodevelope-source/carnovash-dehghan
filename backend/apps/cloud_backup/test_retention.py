from datetime import datetime, timedelta
from unittest import TestCase
from zoneinfo import ZoneInfo
from .retention import Archive, plan_retention


class RetentionTests(TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 27, tzinfo=ZoneInfo('Asia/Tehran'))

    def archive(self, day, name, kind='full', verified=True):
        return Archive(name, self.now-timedelta(days=day), kind, verified)

    def test_preserves_dependent_base_and_recent_chains(self):
        archives = [self.archive(65, 'full-old'), self.archive(64, 'delta-old', 'incremental'),
                    self.archive(40, 'full-base'), self.archive(28, 'delta-recent', 'incremental'),
                    self.archive(20, 'full-20'), self.archive(10, 'full-10'), self.archive(0, 'full-now')]
        kept, dropped = plan_retention(archives, self.now)
        self.assertIn('full-base', [a.name for a in kept])
        self.assertIn('delta-recent', [a.name for a in kept])
        self.assertEqual({a.name for a in dropped}, {'full-old', 'delta-old'})

    def test_invalid_chain_is_never_pruned(self):
        for archives in ([self.archive(2, 'orphan', 'incremental')],
                         [self.archive(2, 'unverified', verified=False)],
                         [self.archive(2, 'same'), self.archive(1, 'same')]):
            with self.assertRaises(ValueError):
                plan_retention(archives, self.now)

    def test_minimum_three_chains_even_if_expired(self):
        archives = [self.archive(day, f'full-{day}') for day in (100, 90, 80, 70)]
        kept, dropped = plan_retention(archives, self.now)
        self.assertEqual(len(kept), 3)
        self.assertEqual([a.name for a in dropped], ['full-100'])
