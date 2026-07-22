from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase
from django.contrib.auth import get_user_model

from apps.auth.models import CarWash
from apps.services.models import GeneralSettings
from apps.vehicles.loyalty import (
    apply_loyalty_visit,
    compute_configured_loyalty_discount,
    cycle_visit_position,
    get_or_create_plate_loyalty,
    next_fixed_discount_notice,
    persian_visit_ordinal,
)
from apps.notifications.services import build_vehicle_released_sms


class FixedDiscountNoticeTests(SimpleTestCase):
    def test_skips_zero_milestones_and_uses_next(self):
        settings_obj = SimpleNamespace(
            discount_calculation_mode='fixed',
            fixed_visit_discounts={'2': 0, '5': 15, '10': 20},
        )
        notice = next_fixed_discount_notice(settings_obj, 1)
        self.assertEqual(notice['target_visit'], 5)
        self.assertEqual(notice['text'], 'درصد تخفیف مراجعه پنجم : 15٪')

    def test_after_cycle_continues_to_12_15_20(self):
        settings_obj = SimpleNamespace(
            discount_calculation_mode='fixed',
            fixed_visit_discounts={'2': 10, '5': 15, '10': 20},
        )
        notice = next_fixed_discount_notice(settings_obj, 10)
        self.assertEqual(notice['target_visit'], 12)
        self.assertEqual(notice['text'], 'درصد تخفیف مراجعه دوازدهم : 10٪')

    def test_step_mode_returns_none(self):
        settings_obj = SimpleNamespace(
            discount_calculation_mode='step',
            fixed_visit_discounts={'2': 10, '5': 15, '10': 20},
        )
        self.assertIsNone(next_fixed_discount_notice(settings_obj, 1))

    def test_all_zero_returns_none(self):
        settings_obj = SimpleNamespace(
            discount_calculation_mode='fixed',
            fixed_visit_discounts={'2': 0, '5': 0, '10': 0},
        )
        self.assertIsNone(next_fixed_discount_notice(settings_obj, 1))


class CycleVisitPositionTests(SimpleTestCase):
    def test_positions_wrap_every_ten_visits(self):
        self.assertEqual(cycle_visit_position(2), 2)
        self.assertEqual(cycle_visit_position(10), 10)
        self.assertEqual(cycle_visit_position(12), 2)
        self.assertEqual(cycle_visit_position(15), 5)
        self.assertEqual(cycle_visit_position(20), 10)

    def test_persian_ordinals(self):
        self.assertEqual(persian_visit_ordinal(2), 'دوم')
        self.assertEqual(persian_visit_ordinal(12), 'دوازدهم')
        self.assertEqual(persian_visit_ordinal(20), 'بیستم')


class LoyaltyCycleResetTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.tenant = CarWash.objects.create(name='Loyalty Wash', slug='loyalty-cycle')
        self.manager = user_model.objects.create_user(
            username='loyalty-cycle-manager',
            password='pass12345',
            phone='09121110000',
            role='manager',
            tenant=self.tenant,
        )
        self.settings = GeneralSettings.objects.create(
            tenant=self.tenant,
            discount_calculation_mode='fixed',
            fixed_visit_discounts={'2': 10, '5': 15, '10': 20},
            discount_percent_per_half_star=Decimal('1'),
        )

    def test_score_resets_after_ten_visits_but_count_continues(self):
        profile = get_or_create_plate_loyalty(
            tenant=self.tenant,
            plate_number='11 ب 111 11',
            plate_left='11',
            plate_letter='ب',
            plate_mid='111',
            plate_right='11',
        )
        for _ in range(10):
            profile = apply_loyalty_visit(profile, discount_percent_per_half_star=Decimal('1'))

        self.assertEqual(profile.visit_count, 10)
        self.assertEqual(profile.cycle_visit_count, 0)
        self.assertEqual(profile.score, Decimal('0'))
        self.assertEqual(getattr(profile, '_loyalty_visit_score'), Decimal('5.0'))

        percent, _amount = compute_configured_loyalty_discount(
            base_amount=100000,
            profile=profile,
            settings_obj=self.settings,
            visit_count=12,
        )
        self.assertEqual(percent, Decimal('10'))

        profile = apply_loyalty_visit(profile, discount_percent_per_half_star=Decimal('1'))
        self.assertEqual(profile.visit_count, 11)
        self.assertEqual(profile.cycle_visit_count, 1)
        self.assertEqual(profile.score, Decimal('0.5'))


class ReleasedSmsFixedDiscountTests(SimpleTestCase):
    def test_fixed_mode_writes_milestone_line(self):
        settings_obj = SimpleNamespace(
            discount_calculation_mode='fixed',
            fixed_visit_discounts={'2': 0, '5': 15, '10': 20},
            sms_vehicle_released_template=(
                'امتیاز شما: [امتیاز مشتری] از ۵\n'
                'درصد تخفیف مراجعه بعد: [درصد تخفیف مراجعه بعد]\n'
                'مبلغ نهایی: [مبلغ نهایی]'
            ),
        )
        vehicle = SimpleNamespace(
            driver_name='علی',
            driver_gender='male',
            tenant=SimpleNamespace(name='کارواش تست'),
            admission_number=1001,
            id=1,
            plate_number='11 ب 111 11',
            plate_left='11',
            plate_letter='ب',
            plate_mid='111',
            plate_right='11',
            plate_type='car',
            released_at=None,
            updated_at=None,
            customer=None,
        )
        text, _context = build_vehicle_released_sms(
            settings_obj,
            vehicle,
            visit_count=1,
            customer_score=0.5,
            next_discount_percent=0,
        )
        self.assertIn('درصد تخفیف مراجعه پنجم : ۱۵٪', text)
        self.assertNotIn('درصد تخفیف مراجعه بعد: درصد تخفیف مراجعه', text)

    def test_step_mode_keeps_generic_percent(self):
        settings_obj = SimpleNamespace(
            discount_calculation_mode='step',
            fixed_visit_discounts={},
            sms_vehicle_released_template='درصد تخفیف مراجعه بعد: [درصد تخفیف مراجعه بعد]',
            discount_percent_per_half_star=1,
        )
        vehicle = SimpleNamespace(
            driver_name='علی',
            driver_gender='male',
            tenant=SimpleNamespace(name='کارواش تست'),
            admission_number=1001,
            id=1,
            plate_number='11 ب 111 11',
            plate_left='11',
            plate_letter='ب',
            plate_mid='111',
            plate_right='11',
            plate_type='car',
            released_at=None,
            updated_at=None,
            customer=None,
        )
        text, _context = build_vehicle_released_sms(
            settings_obj,
            vehicle,
            visit_count=3,
            customer_score=1.5,
            next_discount_percent=3,
        )
        self.assertIn('درصد تخفیف مراجعه بعد: ۳٪', text)
        self.assertNotIn('درصد تخفیف مراجعه دوم', text)
