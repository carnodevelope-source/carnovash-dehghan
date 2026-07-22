from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cw_auth', '0014_expand_feature_purchase_catalog'),
    ]

    operations = [
        migrations.AddField(
            model_name='carwash',
            name='trial_started_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='carwash',
            name='trial_ends_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
