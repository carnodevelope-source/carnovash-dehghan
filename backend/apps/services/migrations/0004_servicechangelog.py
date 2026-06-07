from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('cw_auth', '0008_supportticket_customer_feedback_and_more'),
        ('services', '0003_generalsettings_tenant_service_tenant_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ServiceChangeLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('action_type', models.CharField(choices=[('created', 'Created'), ('updated', 'Updated'), ('deactivated', 'Deactivated'), ('deleted', 'Deleted')], default='updated', max_length=20)),
                ('name_snapshot', models.CharField(max_length=120)),
                ('base_price_snapshot', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('estimated_duration_snapshot', models.PositiveIntegerField(default=30)),
                ('is_active_snapshot', models.BooleanField(default=True)),
                ('change_summary', models.JSONField(blank=True, default=dict)),
                ('changed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='service_change_logs_created', to=settings.AUTH_USER_MODEL)),
                ('service', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='change_logs', to='services.service')),
                ('tenant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='service_change_logs', to='cw_auth.carwash')),
            ],
            options={
                'ordering': ['-created_at', '-id'],
            },
        ),
    ]
