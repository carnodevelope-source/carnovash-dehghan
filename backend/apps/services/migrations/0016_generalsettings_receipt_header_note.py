from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0015_vehicle_auto_sms_setting'),
    ]

    operations = [
        migrations.AddField(
            model_name='generalsettings',
            name='receipt_header_note',
            field=models.TextField(blank=True),
        ),
    ]
