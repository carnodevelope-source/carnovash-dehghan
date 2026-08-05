from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cw_auth', '0017_carwash_exclude_from_hq_reports'),
    ]

    operations = [
        migrations.AddField(
            model_name='carwash',
            name='is_sample',
            field=models.BooleanField(
                default=False,
                help_text='Demo/sample tenant: hidden from HQ reports/lists, tickets still visible.',
            ),
        ),
        migrations.AddField(
            model_name='carwash',
            name='sample_daily_sms_limit',
            field=models.PositiveIntegerField(default=15),
        ),
        migrations.AddField(
            model_name='carwash',
            name='sample_daily_vehicle_limit',
            field=models.PositiveIntegerField(default=20),
        ),
        migrations.AlterField(
            model_name='user',
            name='phone',
            field=models.CharField(db_index=True, max_length=20),
        ),
    ]
