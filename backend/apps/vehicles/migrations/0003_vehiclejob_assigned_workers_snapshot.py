from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vehicles', '0002_vehiclejobservice_is_completed'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehiclejob',
            name='assigned_workers_snapshot',
            field=models.JSONField(blank=True, default=list),
        ),
    ]

