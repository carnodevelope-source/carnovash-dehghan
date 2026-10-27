from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('cloud_backup', '0002_backuprun_backup_kind_backuprun_base_run_id_and_more')]
    operations = [migrations.AddField(model_name='backuprun', name='scheduled_for',
        field=models.DateField(blank=True, db_index=True, null=True))]
