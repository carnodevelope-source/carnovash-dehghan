from django.db import migrations, models
import django.db.models.deletion


def seed_default_accounts(apps, schema_editor):
    Account = apps.get_model('accounting', 'Account')
    defaults = [
        ('1101', 'Cash', 'asset'),
        ('1301', 'Accounts Receivable', 'asset'),
        ('1501', 'Inventory', 'asset'),
        ('2101', 'Accounts Payable', 'liability'),
        ('4101', 'Sales Revenue', 'revenue'),
    ]
    for code, name, nature in defaults:
        Account.objects.get_or_create(code=code, defaults={'name': name, 'nature': nature, 'is_active': True})


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Party',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=150)),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('party_type', models.CharField(choices=[('supplier', 'Supplier'), ('customer', 'Customer'), ('both', 'Both')], default='both', max_length=20)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='journalentry',
            name='voucher_no',
            field=models.CharField(default='TEMP-VOUCHER-NO', max_length=60, unique=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='purchaseinvoice',
            name='supplier',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='purchase_invoices', to='accounting.party'),
        ),
        migrations.AddField(
            model_name='purchaseinvoiceline',
            name='discount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='purchaseinvoiceline',
            name='tax',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='salesinvoice',
            name='customer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='sales_invoices', to='accounting.party'),
        ),
        migrations.AddField(
            model_name='salesinvoice',
            name='settlement_type',
            field=models.CharField(choices=[('cash', 'Cash'), ('card', 'Card'), ('credit', 'Credit')], default='cash', max_length=20),
        ),
        migrations.AddField(
            model_name='salesinvoiceline',
            name='discount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='salesinvoiceline',
            name='tax',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.RemoveField(
            model_name='purchaseinvoice',
            name='supplier_name',
        ),
        migrations.RemoveField(
            model_name='purchaseinvoice',
            name='supplier_phone',
        ),
        migrations.RemoveField(
            model_name='salesinvoice',
            name='customer_name',
        ),
        migrations.RemoveField(
            model_name='salesinvoice',
            name='customer_phone',
        ),
        migrations.RunPython(seed_default_accounts, migrations.RunPython.noop),
    ]
