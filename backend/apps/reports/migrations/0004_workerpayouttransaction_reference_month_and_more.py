from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0003_workerpayouttransaction'),
    ]

    operations = [
        migrations.AddField(
            model_name='workerpayouttransaction',
            name='reference_month',
            field=models.CharField(blank=True, default='', max_length=7),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='workerpayouttransaction',
            name='kind',
            field=models.CharField(
                choices=[
                    ('wage_payment', 'Wage Payment'),
                    ('tip_payment', 'Tip Payment'),
                    ('insurance_payment', 'Insurance Payment'),
                    ('bonus', 'Bonus'),
                    ('penalty', 'Penalty'),
                ],
                max_length=20,
            ),
        ),
        migrations.AddIndex(
            model_name='workerpayouttransaction',
            index=models.Index(fields=['worker', 'kind', 'reference_month'], name='rpt_wrk_kind_mon_idx'),
        ),
    ]
