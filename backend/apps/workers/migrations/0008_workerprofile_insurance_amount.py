from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workers', '0007_workerprofile_started_at_address'),
    ]

    operations = [
        migrations.AddField(
            model_name='workerprofile',
            name='insurance_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
    ]
