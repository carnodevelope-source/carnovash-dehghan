from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('vehicles', '0024_alter_vehiclejob_worker_payment_type')]

    operations = [
        # Install tenant uniqueness BEFORE dropping global uniqueness. There is
        # no intermediate window without a uniqueness constraint, nor data edits.
        migrations.AddConstraint(
            model_name='customerprofile',
            constraint=models.UniqueConstraint(fields=('tenant', 'phone'), name='uniq_customer_phone_per_tenant'),
        ),
        migrations.AlterField(
            model_name='customerprofile', name='phone',
            field=models.CharField(db_index=True, max_length=20),
        ),
    ]
