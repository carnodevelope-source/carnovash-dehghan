from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0020_update_assignment_sms_template_default'),
    ]

    operations = [
        migrations.AddField(
            model_name='generalsettings',
            name='discount_calculation_mode',
            field=models.CharField(
                choices=[('step', 'Step'), ('fixed', 'Fixed')],
                default='step',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='generalsettings',
            name='fixed_visit_discounts',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
