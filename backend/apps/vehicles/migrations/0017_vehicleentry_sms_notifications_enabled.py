from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vehicles', '0016_driver_gender'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehicleentry',
            name='sms_notifications_enabled',
            field=models.BooleanField(default=True),
        ),
    ]
