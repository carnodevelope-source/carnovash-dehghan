from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0005_generalsettings_payment_method_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='generalsettings',
            name='receipt_auto_print',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='generalsettings',
            name='receipt_footer_note',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='generalsettings',
            name='receipt_print_copies',
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='generalsettings',
            name='receipt_printer_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='generalsettings',
            name='receipt_printer_name',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='generalsettings',
            name='receipt_printer_paper_width',
            field=models.CharField(blank=True, default='80mm', max_length=20),
        ),
        migrations.AddField(
            model_name='generalsettings',
            name='receipt_show_logo',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='generalsettings',
            name='receipt_show_qr',
            field=models.BooleanField(default=False),
        ),
    ]
