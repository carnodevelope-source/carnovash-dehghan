from django.db import migrations, models


ASSIGNED_TEMPLATE = (
    '[نام مشتری] عزیز\n'
    'خودروی شما با\n'
    'شماره پذیرش: [شماره پذیرش] با پلاک [پلاک]، در ساعت [ساعت تخصیص]، روز [تاریخ تخصیص] در مجموعه کارواش [نام کارواش] '
    'برای انجام خدمات، پذیرش شد.'
)

ASSIGNED_INVOICE_TEMPLATE = (
    'پیش فاکتور خدمات:\n'
    '[خلاصه خدمات]\n'
    'جمع کل: [جمع کل]\n'
    'تخفیف این سفارش: [جمع تخفیف]\n'
    'مبلغ نهایی بعد از تخفیف: [مبلغ نهایی]\n'
    'خودروی شما حدود 30 دقیقه دیگر آماده ترخیص است.\n'
    'از اعتماد شما سپاسگزاریم.'
)


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0017_generalsettings_sms_template_toggles'),
    ]

    operations = [
        migrations.AlterField(
            model_name='generalsettings',
            name='sms_vehicle_assigned_template',
            field=models.TextField(blank=True, default=ASSIGNED_TEMPLATE),
        ),
        migrations.AlterField(
            model_name='generalsettings',
            name='sms_vehicle_assigned_invoice_template',
            field=models.TextField(blank=True, default=ASSIGNED_INVOICE_TEMPLATE),
        ),
    ]
