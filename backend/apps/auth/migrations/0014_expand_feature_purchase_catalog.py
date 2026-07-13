from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cw_auth', '0013_user_soft_delete_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='carwashfeaturepurchase',
            name='feature_key',
            field=models.CharField(
                choices=[
                    ('core_software', 'Core Software'),
                    ('excel_import', 'Excel Import'),
                    ('attendance', 'Attendance'),
                    ('sms_club', 'SMS Club'),
                    ('accounting', 'Accounting'),
                    ('cloud_storage', 'Cloud Storage'),
                ],
                max_length=50,
            ),
        ),
    ]
