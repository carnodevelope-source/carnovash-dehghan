from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cw_auth', '0011_supportticketattachment'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='supportticket',
            name='is_registration_request',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='PendingTenantRegistration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=20)),
                ('temp_password', models.CharField(blank=True, default='', max_length=128)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('manager', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pending_tenant_registrations', to=settings.AUTH_USER_MODEL)),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_tenant_registrations', to=settings.AUTH_USER_MODEL)),
                ('support_ticket', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='registration_request', to='cw_auth.supportticket')),
                ('tenant', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='pending_registration', to='cw_auth.carwash')),
            ],
            options={
                'ordering': ['-created_at', '-id'],
            },
        ),
    ]
