from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workers', '0006_workerprofile_entrusted_items'),
    ]

    operations = [
        migrations.AddField(
            model_name='workerprofile',
            name='address',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='workerprofile',
            name='started_at',
            field=models.DateField(blank=True, null=True),
        ),
    ]
