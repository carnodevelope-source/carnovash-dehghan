from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0010_service_soft_delete_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='generalsettings',
            name='tax_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='generalsettings',
            name='tax_percent',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
    ]
