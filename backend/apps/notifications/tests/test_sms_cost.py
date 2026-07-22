from decimal import Decimal

from django.test import SimpleTestCase, override_settings

from apps.notifications.services import sms_cost_for_text, sms_segments_for_text


@override_settings(SMS_PRICE_PER_SEGMENT=185, SMS_CHARS_PER_SEGMENT=100)
class SmsCostByCharacterTests(SimpleTestCase):
    def test_empty_text_costs_zero(self):
        self.assertEqual(sms_segments_for_text(''), 0)
        self.assertEqual(sms_cost_for_text(''), Decimal('0'))

    def test_first_hundred_characters_cost_one_segment(self):
        self.assertEqual(sms_segments_for_text('a' * 1), 1)
        self.assertEqual(sms_segments_for_text('a' * 100), 1)
        self.assertEqual(sms_cost_for_text('a' * 100), Decimal('185'))

    def test_second_hundred_characters_cost_two_segments(self):
        self.assertEqual(sms_segments_for_text('a' * 101), 2)
        self.assertEqual(sms_segments_for_text('a' * 200), 2)
        self.assertEqual(sms_cost_for_text('a' * 200), Decimal('370'))
