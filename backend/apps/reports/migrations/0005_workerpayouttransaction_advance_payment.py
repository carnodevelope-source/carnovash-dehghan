from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0004_workerpayouttransaction_reference_month_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='workerpayouttransaction',
            name='kind',
            field=models.CharField(
                choices=[
                    ('wage_payment', 'Wage Payment'),
                    ('tip_payment', 'Tip Payment'),
                    ('insurance_payment', 'Insurance Payment'),
                    ('advance_payment', 'Advance Payment'),
                    ('bonus', 'Bonus'),
                    ('penalty', 'Penalty'),
                ],
                max_length=20,
            ),
        ),
    ]
