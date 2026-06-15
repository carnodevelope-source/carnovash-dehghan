from django.db import migrations, models


def seed_attendance_for_blue_carwash(apps, schema_editor):
    CarWash = apps.get_model('cw_auth', 'CarWash')
    CarWashFeaturePurchase = apps.get_model('cw_auth', 'CarWashFeaturePurchase')
    blue_names = ['کارواش آبی', 'کارواش ابی', 'کارواش آبي']
    tenants = CarWash.objects.filter(name__in=blue_names)
    for tenant in tenants:
        CarWashFeaturePurchase.objects.update_or_create(
            tenant=tenant,
            feature_key='attendance',
            defaults={'is_active': True},
        )


class Migration(migrations.Migration):
    dependencies = [
        ('cw_auth', '0008_supportticket_customer_feedback_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='CarWashFeaturePurchase',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('feature_key', models.CharField(choices=[('attendance', 'Attendance')], max_length=50)),
                ('is_active', models.BooleanField(default=True)),
                ('purchased_at', models.DateTimeField(auto_now_add=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='feature_purchases', to='cw_auth.carwash')),
            ],
            options={
                'ordering': ['tenant_id', 'feature_key'],
            },
        ),
        migrations.AddConstraint(
            model_name='carwashfeaturepurchase',
            constraint=models.UniqueConstraint(fields=('tenant', 'feature_key'), name='uniq_carwash_feature_purchase'),
        ),
        migrations.RunPython(seed_attendance_for_blue_carwash, migrations.RunPython.noop),
    ]
