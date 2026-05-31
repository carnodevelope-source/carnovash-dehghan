from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vehicles', '0004_customerprofile_vehicleentry_customer'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehiclejob',
            name='tip_paid_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='vehiclejob',
            name='worker_share_paid_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
