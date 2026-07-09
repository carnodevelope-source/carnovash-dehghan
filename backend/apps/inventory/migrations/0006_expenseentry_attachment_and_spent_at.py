from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0005_rename_inv_exp_src_spent_idx_inventory_e_source__ecab7e_idx'),
    ]

    operations = [
        migrations.AddField(
            model_name='expenseentry',
            name='attachment',
            field=models.FileField(blank=True, null=True, upload_to='expenses/%Y/%m/'),
        ),
        migrations.AddField(
            model_name='expenseentry',
            name='attachment_original_name',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='expenseentry',
            name='spent_at',
            field=models.DateTimeField(default=timezone.now),
        ),
    ]
