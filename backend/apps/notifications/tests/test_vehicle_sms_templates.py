from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase
from django.utils import timezone

from apps.notifications.services import (
    build_vehicle_assignment_sms,
    build_vehicle_released_sms,
    make_json_safe,
)


class VehicleSmsTemplateTests(SimpleTestCase):
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
        self.assertIn('شست‌وشوی ویژه ---- ۷۵۰،۰۰۰ تومان', message)
        self.assertIn('واکس بدنه ---- ۵۰۰،۰۰۰ تومان', message)
        self.assertIn('۱،۲۵۰،۰۰۰ تومان', message)

    def test_released_sms_uses_fallback_greeting_for_anonymous_customer(self):
        tenant = SimpleNamespace(name='کارواش یک')
        vehicle = SimpleNamespace(
            tenant=tenant,
            driver_name='',
            plate_number='22 ب 345 67',
            released_at=timezone.now(),
            updated_at=timezone.now(),
        )
        settings_obj = SimpleNamespace(
            sms_vehicle_released_template='[خطاب مشتری]\n[امتیاز مشتری]\n[درصد تخفیف سفارش بعد]'
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
        self.assertIn('۴.۵', message)
        self.assertIn('۴۵٪', message)
        self.assertIn('تعداد دفعات مراجعه: ۰', message)
        self.assertIn('انعام: ۰ تومان', message)

    def test_released_sms_keeps_visit_count_and_tip_in_legacy_templates(self):
        tenant = SimpleNamespace(name='کارواش یک')
        vehicle = SimpleNamespace(
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
