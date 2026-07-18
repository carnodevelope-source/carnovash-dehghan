from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0016_generalsettings_receipt_header_note'),
    ]

    operations = [
        migrations.AddField(
            model_name='generalsettings',
            name='sms_vehicle_assigned_enabled',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='generalsettings',
            name='sms_vehicle_assigned_invoice_enabled',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='generalsettings',
            name='sms_vehicle_released_enabled',
            field=models.BooleanField(default=True),
        ),
    ]
