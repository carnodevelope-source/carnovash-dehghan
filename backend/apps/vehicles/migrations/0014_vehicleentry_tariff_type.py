from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vehicles', '0013_vehicleentry_plate_type_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehicleentry',
            name='tariff_type',
            field=models.CharField(
                choices=[
                    ('type_1', 'Type 1'),
                    ('type_2', 'Type 2'),
                    ('type_3', 'Type 3'),
                    ('type_4', 'Type 4'),
                ],
                default='type_1',
                max_length=20,
            ),
        ),
    ]
