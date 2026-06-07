from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workers', '0003_rename_workers_wor_worker__e8b5dd_idx_workers_wor_worker__0afca6_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='workerprofile',
            name='has_entrusted_item',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='workerprofile',
            name='entrusted_item_description',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='workerprofile',
            name='entrusted_item_quantity',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='workerprofile',
            name='entrusted_item_price',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
    ]
