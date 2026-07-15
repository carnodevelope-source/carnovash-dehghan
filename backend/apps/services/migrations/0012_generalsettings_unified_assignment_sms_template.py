from django.db import migrations, models


ASSIGNED_TEMPLATE = (
    '[خطاب مشتری]\n'
    'خودروی شما با پلاک [پلاک] در ساعت [ساعت تخصیص] روز [تاریخ تخصیص] در کارواش [نام کارواش] '
    'برای انجام خدمات ثبت و تخصیص داده شد.\n\n'
    'پیش فاکتور خدمات:\n'
    '[خلاصه خدمات]\n'
    'جمع کل: [جمع کل]\n'
    'خودروی شما حدود 1 ساعت کاری دیگر آماده ترخیص است.\n'
    'از اعتماد شما سپاسگزاریم.'
)


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0011_generalsettings_tax_fields'),
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
            field=models.TextField(blank=True, default=''),
        ),
    ]
