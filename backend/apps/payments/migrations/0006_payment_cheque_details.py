from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0005_walletgatewayrequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='cheque_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='payment',
            name='cheque_sayadi_number',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name='payment',
            name='cheque_serial_number',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name='payment',
            name='cheque_shaba',
            field=models.CharField(blank=True, max_length=40),
        ),
    ]
