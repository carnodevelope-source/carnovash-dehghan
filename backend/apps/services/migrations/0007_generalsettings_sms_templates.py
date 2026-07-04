from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0006_generalsettings_receipt_printer_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='generalsettings',
            name='sms_vehicle_assigned_invoice_template',
            field=models.TextField(blank=True, default='پیش فاکتور خدمات:\n[خلاصه خدمات]\nجمع کل: [جمع کل]\nخودروی شما حدود ۳ ساعت کاری دیگر آماده ترخیص است.\n[نام کارواش]\n----------------------'),
        ),
        migrations.AddField(
            model_name='generalsettings',
            name='sms_vehicle_assigned_template',
            field=models.TextField(blank=True, default='[خطاب مشتری]\nخودروی شما با پلاک [پلاک] در ساعت [ساعت تخصیص] روز [تاریخ تخصیص] در [نام کارواش] برای انجام خدمات ثبت و تخصیص داده شد.'),
        ),
        migrations.AddField(
            model_name='generalsettings',
            name='sms_vehicle_released_template',
            field=models.TextField(blank=True, default='[خطاب مشتری]\nخودروی شما در ساعت [ساعت ترخیص] روز [تاریخ ترخیص] از [نام کارواش] ترخیص شد.\nامتیاز شما: [امتیاز مشتری] از ۵\nدرصد تخفیف سفارش بعد: [درصد تخفیف سفارش بعد]\nمبلغ نهایی: [مبلغ نهایی]\nجمع تخفیف: [جمع تخفیف]\n[نام کارواش]'),
        ),
    ]
