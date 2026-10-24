from unittest import TestCase
from types import SimpleNamespace

from apps.notifications.sms_text import ltr_sms_fragment, prepare_sms_text


class SmsTextDirectionTests(TestCase):
    def test_plate_components_keep_requested_left_to_right_order(self):
        from apps.notifications.services import format_plate_for_sms

        vehicle = SimpleNamespace(
            plate_type='car', plate_left='54', plate_letter='و',
            plate_mid='123', plate_right='94',
        )
        plate = format_plate_for_sms(vehicle)
        self.assertEqual(plate, '\u2066\u202d94 - 123 و 54\u202c\u2069')
        message = prepare_sms_text(f'پلاک {plate}، در ساعت ۱۹:۳۲ پذیرش شد.')
        self.assertTrue(message.startswith('\u200f'))
        self.assertIn(plate, message)

    def test_ltr_fragment_closes_direction_before_following_text(self):
        self.assertEqual(ltr_sms_fragment('94 - 123 و 54'), '\u2066\u202d94 - 123 و 54\u202c\u2069')

    def test_mixed_paragraphs_start_with_rtl_mark(self):
        self.assertEqual(
            prepare_sms_text('CarnoWash کارنوواش\n123 مبلغ پرداخت\nhttps://example.com'),
            '\u200fCarnoWash کارنوواش\n\u200f123 مبلغ پرداخت\nhttps://example.com',
        )

    def test_preserves_blank_lines_and_line_endings(self):
        self.assertEqual(prepare_sms_text('سلام\r\n\r\nخداحافظ\n'), '\u200fسلام\r\n\r\n\u200fخداحافظ\n')

    def test_preparing_twice_does_not_add_billable_characters(self):
        text = prepare_sms_text('کارنوواش 123')
        self.assertEqual(prepare_sms_text(text), text)

    def test_latin_only_messages_are_preserved(self):
        self.assertEqual(prepare_sms_text('Code: 12345'), 'Code: 12345')
