from decimal import Decimal

from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.utils import timezone

from apps.auth.models import CarWash
from apps.vehicles.loyalty import CYCLE_VISIT_LIMIT, apply_loyalty_visit, rebuild_plate_loyalty
from apps.vehicles.models import PlateLoyaltyProfile, VehicleEntry


DISCOUNT_PER_HALF_STAR = Decimal('1')


def replay_expected_state(check_in_times, *, now):
    """The pre-optimisation algorithm: one apply_loyalty_visit per historical visit."""
    state = {
        'visit_count': 0,
        'cycle_visit_count': 0,
        'score': Decimal('0'),
        'next_discount_percent': Decimal('0'),
        'first_order_at': check_in_times[0] if check_in_times else now,
        'last_cycle_started_at': check_in_times[0] if check_in_times else now,
    }
    for check_in_at in check_in_times:
        moment = timezone.localtime(check_in_at)
        next_cycle = state['cycle_visit_count'] + 1
        if next_cycle > CYCLE_VISIT_LIMIT:
            next_cycle = 1
            state['last_cycle_started_at'] = moment
        earned = min(Decimal('5.0'), Decimal('0.5') * Decimal(str(next_cycle)))
        completed = next_cycle >= CYCLE_VISIT_LIMIT
        state['visit_count'] += 1
        state['cycle_visit_count'] = 0 if completed else next_cycle
        state['score'] = Decimal('0') if completed else earned
        state['next_discount_percent'] = (
            Decimal('0') if completed else DISCOUNT_PER_HALF_STAR * (earned * Decimal('2'))
        )
        if completed:
            state['last_cycle_started_at'] = moment
    return state


class LoyaltyRebuildTests(TestCase):
    def setUp(self):
        self.tenant = CarWash.objects.create(name='Rebuild Wash', slug='loyalty-rebuild')

    def _plate(self, index):
        """Distinct in every component, so lookup variants cannot match another case."""
        left = f'{10 + index:02d}'
        mid = f'{100 + index:03d}'
        right = f'{20 + index:02d}'
        return {
            'plate_left': left,
            'plate_letter': 'A',
            'plate_mid': mid,
            'plate_right': right,
            'plate_number': f'{left} A {mid} {right}',
        }

    def _make_profile(self, plate):
        return PlateLoyaltyProfile.objects.create(
            tenant=self.tenant,
            visit_count=0,
            cycle_visit_count=0,
            score=Decimal('0'),
            **plate,
        )

    def _make_visits(self, plate, count):
        base = timezone.now() - timezone.timedelta(days=count + 1)
        for index in range(count):
            VehicleEntry.objects.create(
                tenant=self.tenant,
                plate_type=VehicleEntry.PlateType.CAR,
                car_model='Pride',
                car_color='White',
                driver_name='Repeat Customer',
                driver_phone='09120000000',
                status=VehicleEntry.Status.ENTERED,
                check_in_at=base + timezone.timedelta(days=index),
                **plate,
            )
        # check_in_at is auto-set on insert, so read back what was actually stored.
        return list(
            VehicleEntry.objects.filter(tenant=self.tenant, plate_number=plate['plate_number'])
            .order_by('check_in_at', 'id')
            .values_list('check_in_at', flat=True)
        )

    def test_matches_visit_by_visit_replay(self):
        # Cover both sides of every cycle boundary up to two full cycles.
        for count in [0, 1, 2, 9, 10, 11, 19, 20, 21, 25]:
            with self.subTest(visits=count):
                plate = self._plate(count)
                times = self._make_visits(plate, count)
                profile = self._make_profile(plate)
                now = timezone.now()

                rebuilt = rebuild_plate_loyalty(
                    profile,
                    discount_percent_per_half_star=DISCOUNT_PER_HALF_STAR,
                    now=now,
                )
                expected = replay_expected_state(times, now=timezone.localtime(now))

                self.assertEqual(rebuilt.visit_count, expected['visit_count'])
                self.assertEqual(rebuilt.cycle_visit_count, expected['cycle_visit_count'])
                self.assertEqual(rebuilt.score, expected['score'])
                self.assertEqual(rebuilt.next_discount_percent, expected['next_discount_percent'])
                self.assertEqual(rebuilt.first_order_at, expected['first_order_at'])
                self.assertEqual(rebuilt.last_cycle_started_at, expected['last_cycle_started_at'])

    def test_query_count_does_not_grow_with_visit_history(self):
        short_plate = self._plate(80)
        long_plate = self._plate(81)
        self._make_visits(short_plate, 3)
        self._make_visits(long_plate, 60)
        short_profile = self._make_profile(short_plate)
        long_profile = self._make_profile(long_plate)

        with CaptureQueriesContext(connection) as short_queries:
            rebuild_plate_loyalty(short_profile, discount_percent_per_half_star=DISCOUNT_PER_HALF_STAR)
        with CaptureQueriesContext(connection) as long_queries:
            rebuild_plate_loyalty(long_profile, discount_percent_per_half_star=DISCOUNT_PER_HALF_STAR)

        self.assertEqual(len(short_queries), len(long_queries))
        self.assertLessEqual(len(long_queries), 3)

    def test_apply_loyalty_visit_still_advances_one_step(self):
        plate = self._plate(90)
        self._make_visits(plate, 4)
        profile = self._make_profile(plate)
        rebuild_plate_loyalty(profile, discount_percent_per_half_star=DISCOUNT_PER_HALF_STAR)

        advanced = apply_loyalty_visit(profile, discount_percent_per_half_star=DISCOUNT_PER_HALF_STAR)
        self.assertEqual(advanced.visit_count, 5)
        self.assertEqual(advanced.cycle_visit_count, 5)
        self.assertEqual(advanced.score, Decimal('2.5'))
