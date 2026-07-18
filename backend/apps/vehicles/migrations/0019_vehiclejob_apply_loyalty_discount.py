from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vehicles', '0018_vehicleentry_admission_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehiclejob',
            name='apply_loyalty_discount',
            field=models.BooleanField(default=True),
        ),
    ]
