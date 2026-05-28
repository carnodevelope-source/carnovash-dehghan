from django.db import migrations, models


def seed_more_accounts(apps, schema_editor):
    Account = apps.get_model('accounting', 'Account')
    defaults = [
        ('1102', 'Bank', 'asset'),
        ('1103', 'Card Reader', 'asset'),
        ('1301', 'Customers Receivable', 'asset'),
        ('2101', 'Suppliers Payable', 'liability'),
    ]
    for code, name, nature in defaults:
        Account.objects.get_or_create(code=code, defaults={'name': name, 'nature': nature, 'is_active': True})


class Migration(migrations.Migration):
    dependencies = [
        ('accounting', '0002_accounting_panel_upgrade'),
    ]

    operations = [
        migrations.AddField(
            model_name='party',
            name='address',
            field=models.TextField(blank=True, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='party',
            name='mobile',
            field=models.CharField(blank=True, default='', max_length=20),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='party',
            name='national_id',
            field=models.CharField(blank=True, default='', max_length=20),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='purchaseinvoice',
            name='description',
            field=models.TextField(blank=True, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='purchaseinvoice',
            name='grand_total',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='purchaseinvoice',
            name='payment_type',
            field=models.CharField(choices=[('cash', 'Cash'), ('bank', 'Bank'), ('mixed', 'Mixed'), ('credit', 'Credit')], default='cash', max_length=20),
        ),
        migrations.AddField(
            model_name='purchaseinvoice',
            name='remaining_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='purchaseinvoice',
            name='status',
            field=models.CharField(choices=[('draft', 'Draft'), ('confirmed', 'Confirmed'), ('cancelled', 'Cancelled')], default='draft', max_length=20),
        ),
        migrations.AddField(
            model_name='purchaseinvoice',
            name='total_discount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='purchaseinvoice',
            name='total_tax',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='purchaseinvoiceline',
            name='description',
            field=models.CharField(blank=True, default='', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='purchaseinvoiceline',
            name='total',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='salesinvoice',
            name='description',
            field=models.TextField(blank=True, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='salesinvoice',
            name='grand_total',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='salesinvoice',
            name='remaining_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='salesinvoice',
            name='status',
            field=models.CharField(choices=[('draft', 'Draft'), ('confirmed', 'Confirmed'), ('cancelled', 'Cancelled')], default='draft', max_length=20),
        ),
        migrations.AddField(
            model_name='salesinvoice',
            name='subtotal',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='salesinvoice',
            name='total_discount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='salesinvoice',
            name='total_tax',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='salesinvoiceline',
            name='description',
            field=models.CharField(blank=True, default='', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='salesinvoiceline',
            name='total',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.RemoveField(model_name='purchaseinvoice', name='discount'),
        migrations.RemoveField(model_name='purchaseinvoice', name='tax'),
        migrations.RemoveField(model_name='purchaseinvoice', name='total'),
        migrations.RemoveField(model_name='purchaseinvoice', name='notes'),
        migrations.RemoveField(model_name='purchaseinvoiceline', name='line_total'),
        migrations.RemoveField(model_name='salesinvoice', name='subtotal_services'),
        migrations.RemoveField(model_name='salesinvoice', name='subtotal_products'),
        migrations.RemoveField(model_name='salesinvoice', name='discount'),
        migrations.RemoveField(model_name='salesinvoice', name='tax'),
        migrations.RemoveField(model_name='salesinvoice', name='tip_amount'),
        migrations.RemoveField(model_name='salesinvoice', name='total'),
        migrations.RemoveField(model_name='salesinvoiceline', name='line_total'),
        migrations.RunPython(seed_more_accounts, migrations.RunPython.noop),
    ]
