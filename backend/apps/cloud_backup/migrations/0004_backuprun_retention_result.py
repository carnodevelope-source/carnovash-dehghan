from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('cloud_backup','0003_backuprun_scheduled_for')]
    operations = [
        migrations.AddField(model_name='backuprun',name='retention_status',field=models.CharField(default='not_run',max_length=16)),
        migrations.AddField(model_name='backuprun',name='retention_error_code',field=models.CharField(blank=True,max_length=48)),
        migrations.AddField(model_name='backuprun',name='retention_checked_at',field=models.DateTimeField(null=True)),
    ]
