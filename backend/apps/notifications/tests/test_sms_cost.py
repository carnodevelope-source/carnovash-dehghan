from decimal import Decimal

from django.test import SimpleTestCase, override_settings

from apps.notifications.services import (
    sms_billable_text,
    sms_cost_for_text,
    sms_segments_for_text,
)


@override_settings(
    SMS_PRICE_PER_SEGMENT=185,
    SMS_CHARS_PER_SEGMENT=70,
    SMS_PROVIDER_FOOTER='\nلغو11',
)
class SmsCostByCharacterTests(SimpleTestCase):
    def test_empty_text_costs_zero(self):
        self.assertEqual(sms_segments_for_text(''), 0)
        self.assertEqual(sms_cost_for_text(''), Decimal('0'))

    def test_first_seventy_characters_cost_one_segment_including_footer(self):
        # body 64 + footer "\nلغو11" (6) = 70 → 1 part
        body = 'a' * 64
        self.assertEqual(len(sms_billable_text(body)), 70)
        self.assertEqual(sms_segments_for_text(body), 1)
        self.assertEqual(sms_cost_for_text(body), Decimal('185'))

    def test_second_part_uses_sixty_seven_chars(self):
        # billable 71 → multipart ceil(71/67)=2
        body = 'a' * 65
        self.assertEqual(len(sms_billable_text(body)), 71)
        self.assertEqual(sms_segments_for_text(body), 2)
        self.assertEqual(sms_cost_for_text(body), Decimal('370'))

    def test_long_persian_style_message_matches_five_parts(self):
        # Melipayamak sample: 282 billable chars → 5 parts (1*70 then 67s)
        body = 'ب' * (282 - len('\nلغو11'))
        self.assertEqual(len(sms_billable_text(body)), 282)
        self.assertEqual(sms_segments_for_text(body), 5)
        self.assertEqual(sms_cost_for_text(body), Decimal('925'))

    def test_cost_scales_with_actual_message_not_flat_fee(self):
        short = 'سلام'
        long = 'سلام\n' + ('خط تست پیامک طولانی. ' * 20)
        self.assertEqual(sms_segments_for_text(short), 1)
        self.assertGreater(sms_segments_for_text(long), sms_segments_for_text(short))
        self.assertGreater(sms_cost_for_text(long), sms_cost_for_text(short))

    def test_existing_cancel_footer_is_not_duplicated(self):
        body = 'پیام تست\nلغو11'
        self.assertEqual(sms_billable_text(body), body)
