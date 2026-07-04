from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0007_generalsettings_sms_templates'),
    ]

    operations = [
        migrations.AddField(
            model_name='generalsettings',
            name='sms_provider_api_key',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='generalsettings',
            name='sms_provider_base_url',
            field=models.CharField(blank=True, default='https://api.iranpayamak.com', max_length=255),
        ),
        migrations.AddField(
            model_name='generalsettings',
            name='sms_provider_line_number',
            field=models.CharField(blank=True, max_length=50),
        ),
    ]
