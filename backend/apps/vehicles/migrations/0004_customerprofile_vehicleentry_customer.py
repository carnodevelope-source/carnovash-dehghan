from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('vehicles', '0003_vehiclejob_assigned_workers_snapshot'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomerProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('phone', models.CharField(db_index=True, max_length=20, unique=True)),
                ('full_name', models.CharField(blank=True, max_length=120)),
                ('yearly_score', models.DecimalField(decimal_places=1, default=0, max_digits=3)),
                ('score_year', models.PositiveSmallIntegerField(default=1400)),
            ],
            options={
                'ordering': ['-updated_at'],
            },
        ),
        migrations.AddField(
            model_name='vehicleentry',
            name='customer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='vehicle_entries', to='vehicles.customerprofile'),
        ),
    ]

