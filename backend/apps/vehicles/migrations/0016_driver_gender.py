from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vehicles', '0015_plate_loyalty_and_discount_buckets'),
    ]

    operations = [
        migrations.AddField(
            model_name='customerprofile',
            name='gender',
            field=models.CharField(blank=True, choices=[('male', 'Male'), ('female', 'Female')], default='', max_length=10),
        ),
        migrations.AddField(
            model_name='vehicleentry',
            name='driver_gender',
            field=models.CharField(blank=True, choices=[('male', 'Male'), ('female', 'Female')], default='', max_length=10),
        ),
    ]
