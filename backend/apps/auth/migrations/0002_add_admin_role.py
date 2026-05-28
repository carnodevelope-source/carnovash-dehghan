from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cw_auth', '0001_initial'),
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
                    ('operator', 'Operator'),
                    ('worker', 'Worker'),
                ],
                default='operator',
                max_length=20,
            ),
        ),
    ]
