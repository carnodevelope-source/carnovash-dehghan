from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('vehicles', '0014_vehicleentry_tariff_type'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PlateLoyaltyProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('plate_number', models.CharField(db_index=True, max_length=20)),
                ('plate_left', models.CharField(blank=True, max_length=2)),
                ('plate_letter', models.CharField(blank=True, max_length=5)),
                ('plate_mid', models.CharField(blank=True, max_length=3)),
                ('plate_right', models.CharField(blank=True, max_length=2)),
                ('score', models.DecimalField(decimal_places=1, default=0, max_digits=3)),
                ('visit_count', models.PositiveIntegerField(default=0)),
                ('cycle_visit_count', models.PositiveIntegerField(default=0)),
                ('last_cycle_started_at', models.DateTimeField(blank=True, null=True)),
                ('first_order_at', models.DateTimeField(blank=True, null=True)),
                ('next_discount_percent', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('is_active', models.BooleanField(default=True)),
                ('tenant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='plate_loyalty_profiles', to='cw_auth.carwash')),
            ],
            options={'ordering': ['-updated_at']},
        ),
        migrations.AddConstraint(
            model_name='plateloyaltyprofile',
            constraint=models.UniqueConstraint(fields=('tenant', 'plate_number'), name='uniq_plate_loyalty_per_tenant'),
        ),
        migrations.AddField(
            model_name='vehiclejob',
            name='facility_discount_locked',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='vehiclejob',
            name='facility_discount_total',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='vehiclejob',
            name='loyalty_discount_total',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='vehiclejob',
            name='service_list_subtotal',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='vehiclejob',
            name='total_discount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='vehiclejobservice',
            name='list_unit_price',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
    ]
