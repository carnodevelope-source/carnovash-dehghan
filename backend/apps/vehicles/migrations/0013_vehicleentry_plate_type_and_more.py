from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("vehicles", "0012_vehicleentry_payment_method"),
    ]

    operations = [
        migrations.AddField(
            model_name="vehicleentry",
            name="plate_type",
            field=models.CharField(
                choices=[("car", "Car"), ("motorcycle", "Motorcycle")],
                default="car",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="blockedplate",
            name="plate_type",
            field=models.CharField(
                choices=[("car", "Car"), ("motorcycle", "Motorcycle")],
                default="car",
                max_length=20,
            ),
        ),
    ]
