# Generated manually to keep the model default and migration state aligned.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0012_generalsettings_unified_assignment_sms_template'),
    ]

    operations = [
        migrations.AlterField(
            model_name='generalsettings',
            name='sms_vehicle_released_template',
            field=models.TextField(
                blank=True,
                default='[خطاب مشتری]\nخودروی شما در ساعت [ساعت ترخیص] روز [تاریخ ترخیص] از کارواش [نام کارواش] ترخیص شد.\nامتیاز شما: [امتیاز مشتری] از ۵\nدرصد تخفیف سفارش بعد: [درصد تخفیف سفارش بعد]\nتعداد دفعات مراجعه: [تعداد مراجعات]\nانعام: [انعام]\nجمع تخفیف: [جمع تخفیف]\nمبلغ نهایی: [مبلغ نهایی]\n[نام کارواش]',
            ),
        ),
    ]
