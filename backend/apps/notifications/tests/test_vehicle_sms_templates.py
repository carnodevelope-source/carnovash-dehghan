from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase
from django.utils import timezone

from apps.notifications.services import (
    build_vehicle_assignment_sms,
    build_vehicle_released_sms,
    customer_display_name_with_title,
    make_json_safe,
)


class VehicleSmsTemplateTests(SimpleTestCase):
    def test_customer_display_name_uses_aghaye_for_male_customer(self):
        self.assertEqual(
            customer_display_name_with_title('علی رضایی', 'male'),
            'آقای علی رضایی',
        )

    def test_make_json_safe_serializes_datetime_and_decimal(self):
        now = timezone.now()
        payload = make_json_safe({
            'assigned_at': now,
            'cost': Decimal('1250.50'),
            'nested': [Decimal('10'), {'released_at': now}],
        })

        self.assertEqual(payload['assigned_at'], now.isoformat())
        self.assertEqual(payload['cost'], 1250.5)
        self.assertEqual(payload['nested'][0], 10.0)
        self.assertEqual(payload['nested'][1]['released_at'], now.isoformat())

    def test_assignment_sms_renders_customer_and_services(self):
        tenant = SimpleNamespace(name='کارواش یک')
        job = SimpleNamespace(
            final_total=1250000,
            services_total=1250000,
            service_lines=[
                SimpleNamespace(custom_service_name='شست‌وشوی ویژه', line_total=750000),
                SimpleNamespace(custom_service_name='واکس بدنه', line_total=500000),
            ],
        )
        vehicle = SimpleNamespace(
            admission_number=1000,
            tenant=tenant,
            job=job,
            driver_name='علی رضایی',
            plate_number='22 ب 345 67',
            ready_at=timezone.now(),
            updated_at=timezone.now(),
        )
        settings_obj = SimpleNamespace(
            sms_vehicle_assigned_template='[خطاب مشتری]\nپلاک: [پلاک]',
            sms_vehicle_assigned_invoice_template='[خلاصه خدمات]\n[جمع کل]',
        )

        message, _context = build_vehicle_assignment_sms(settings_obj, vehicle)

        self.assertIn('علی رضایی عزیز', message)
        self.assertNotIn('[خطاب مشتری]', message)
        self.assertIn('شماره پذیرش: ۱۰۰۰', message)
        self.assertIn('شست‌وشوی ویژه: ۷۵۰،۰۰۰ تومان', message)
        self.assertIn('واکس بدنه: ۵۰۰،۰۰۰ تومان', message)
        self.assertIn('۱،۲۵۰،۰۰۰ تومان', message)
        self.assertLess(message.index('پلاک: 67 - 345 ب 22'), message.index('شست‌وشوی ویژه'))

    def test_assignment_invoice_sms_shows_tariff_discount_and_final_total(self):
        tenant = SimpleNamespace(name='کارواش یک')
        job = SimpleNamespace(
            final_total=300000,
            services_total=300000,
            service_list_subtotal=400000,
            products_total=0,
            total_discount=100000,
            service_lines=[
                SimpleNamespace(custom_service_name='شست‌وشوی کامل', quantity=1, list_unit_price=400000, line_total=300000, discount_amount=100000),
            ],
        )
        vehicle = SimpleNamespace(
            admission_number=1000,
            tenant=tenant,
            job=job,
            driver_name='علی رضایی',
            plate_number='22 ص 377 54',
            plate_left='22',
            plate_letter='ص',
            plate_mid='377',
            plate_right='54',
            ready_at=timezone.now(),
            updated_at=timezone.now(),
        )
        settings_obj = SimpleNamespace(
            sms_vehicle_assigned_template='پلاک: [پلاک]',
            sms_vehicle_assigned_invoice_template='[خلاصه خدمات]\nجمع کل: [جمع کل]',
        )

        message, _context = build_vehicle_assignment_sms(settings_obj, vehicle)

        self.assertIn('پلاک: 54 - 377 ص 22', message)
        self.assertIn('شماره پذیرش: ۱۰۰۰', message)
        self.assertIn('شست‌وشوی کامل: ۴۰۰،۰۰۰ تومان', message)
        self.assertIn('جمع کل: ۴۰۰،۰۰۰ تومان', message)
        self.assertIn('تخفیف این سفارش: ۱۰۰،۰۰۰ تومان', message)
        self.assertIn('مبلغ نهایی بعد از تخفیف: ۳۰۰،۰۰۰ تومان', message)

    def test_default_assignment_sms_is_single_admission_and_invoice_message(self):
        tenant = SimpleNamespace(name='میلان')
        job = SimpleNamespace(
            final_total=265000,
            services_total=265000,
            service_list_subtotal=350000,
            products_total=0,
            total_discount=85000,
            service_lines=[
                SimpleNamespace(custom_service_name='شست‌وشوی کامل', list_unit_price=350000, line_total=265000),
            ],
        )
        vehicle = SimpleNamespace(
            admission_number=1000,
            tenant=tenant,
            job=job,
            driver_name='',
            plate_number='22 ب 345 67',
            ready_at=timezone.now(),
            updated_at=timezone.now(),
        )
        settings_obj = SimpleNamespace(
            sms_vehicle_assigned_template='',
            sms_vehicle_assigned_invoice_template='',
        )

        message, _context = build_vehicle_assignment_sms(settings_obj, vehicle)

        self.assertIn('مشتری عزیز', message)
        self.assertIn('شماره پذیرش: ۱۰۰۰', message)
        self.assertIn('در مجموعه کارواش میلان برای انجام خدمات، پذیرش شد.', message)
        self.assertIn('پیش فاکتور خدمات:', message)
        self.assertIn('شست‌وشوی کامل: ۳۵۰،۰۰۰ تومان', message)
        self.assertIn('جمع کل: ۳۵۰،۰۰۰ تومان', message)
        self.assertIn('تخفیف این سفارش: ۸۵،۰۰۰ تومان', message)
        self.assertIn('مبلغ نهایی بعد از تخفیف: ۲۶۵،۰۰۰ تومان', message)
        self.assertIn('خودروی شما حدود 30 دقیقه دیگر آماده ترخیص است.', message)

    def test_released_sms_uses_fallback_greeting_for_anonymous_customer(self):
        tenant = SimpleNamespace(name='کارواش یک')
        vehicle = SimpleNamespace(
            admission_number=1000,
            tenant=tenant,
            driver_name='',
            plate_number='22 ب 345 67',
            released_at=timezone.now(),
            updated_at=timezone.now(),
        )
        settings_obj = SimpleNamespace(
            sms_vehicle_released_template='[خطاب مشتری]\n[امتیاز مشتری]\nدرصد تخفیف سفارش بعد: [درصد تخفیف سفارش بعد]'
        )

        message, _context = build_vehicle_released_sms(
            settings_obj,
            vehicle,
            customer_score=4.5,
            next_discount_percent=45,
            final_total=1800000,
            discount_total=250000,
        )

        self.assertIn('مشتری عزیز', message)
        self.assertNotIn('[خطاب مشتری]', message)
        self.assertIn('۴.۵', message)
        self.assertIn('۴۵٪', message)
        self.assertIn('درصد تخفیف مراجعه بعد', message)
        self.assertNotIn('سفارش بعد', message)
        self.assertIn('تعداد دفعات مراجعه: ۰', message)
        self.assertIn('انعام: ۰ تومان', message)

    def test_released_sms_keeps_visit_count_and_tip_in_legacy_templates(self):
        tenant = SimpleNamespace(name='کارواش یک')
        vehicle = SimpleNamespace(
            admission_number=1000,
            tenant=tenant,
            driver_name='علی رضایی',
            plate_number='22 ب 345 67',
            released_at=timezone.now(),
            updated_at=timezone.now(),
        )
        settings_obj = SimpleNamespace(
            sms_vehicle_released_template=(
                '[خطاب مشتری]\n'
                'درصد تخفیف سفارش بعد: [درصد تخفیف سفارش بعد]\n'
                'مبلغ نهایی: [مبلغ نهایی]\n'
                'جمع تخفیف: [جمع تخفیف]\n'
                '[نام کارواش]'
            )
        )

        message, _context = build_vehicle_released_sms(
            settings_obj,
            vehicle,
            next_discount_percent=10,
            final_total=265000,
            discount_total=135000,
            visit_count=5,
            tip_amount=50000,
        )

        self.assertIn('تعداد دفعات مراجعه: ۵', message)
        self.assertIn('انعام: ۵۰،۰۰۰ تومان', message)
        self.assertIn('مبلغ نهایی: ۲۶۵،۰۰۰ تومان', message)
