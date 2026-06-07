from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0004_servicechangelog'),
    ]

    operations = [
        migrations.AddField(
            model_name='generalsettings',
            name='bank_account_holder',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='generalsettings',
            name='bank_account_iban',
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AddField(
            model_name='generalsettings',
            name='bank_card_number',
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name='generalsettings',
            name='payment_methods_note',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='generalsettings',
            name='pos_device_name',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='generalsettings',
            name='pos_terminal_id',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name='generalsettings',
            name='preferred_bank_name',
            field=models.CharField(blank=True, max_length=120),
        ),
    ]
