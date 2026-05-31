from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vehicles', '0005_vehiclejob_payout_flags'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehiclejob',
            name='workers_tip_share_amount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
    ]
