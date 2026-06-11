from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cw_auth', '0008_supportticket_customer_feedback_and_more'),
        ('inventory', '0003_stockmovement_sale_price_snapshot'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExpenseEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=180)),
                ('amount', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('details', models.TextField(blank=True)),
                ('source_type', models.CharField(choices=[('manual', 'Manual')], default='manual', max_length=20)),
                ('spent_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='expense_entries_created', to=settings.AUTH_USER_MODEL)),
                ('tenant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='expense_entries', to='cw_auth.carwash')),
            ],
            options={
                'ordering': ['-spent_at', '-id'],
                'indexes': [models.Index(fields=['source_type', 'spent_at'], name='inv_exp_src_spent_idx')],
            },
        ),
    ]
