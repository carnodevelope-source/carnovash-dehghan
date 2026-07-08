from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0008_generalsettings_sms_provider_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='motorcycle_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='service',
            name='motorcycle_pricing_tiers',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='service',
            name='pricing_tiers',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
