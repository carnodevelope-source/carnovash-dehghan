from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cw_auth', '0002_add_admin_role'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('admin', 'Admin'),
                    ('owner', 'Owner'),
                    ('manager', 'Manager'),
                    ('accountant', 'Accountant'),
                    ('operator', 'Operator'),
                    ('worker', 'Worker'),
                ],
                default='operator',
                max_length=20,
            ),
        ),
    ]
