from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('workers', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='workerprofile',
            name='service_share_type',
            field=models.CharField(
                choices=[('percent', 'Percent'), ('fixed', 'Fixed')],
                default='percent',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='workerprofile',
            name='service_share_value',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='workerprofile',
            name='tip_share_percent',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
    ]
