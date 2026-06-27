from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cw_auth', '0009_carwashfeaturepurchase'),
    ]

    operations = [
        migrations.AlterField(
            model_name='carwashfeaturepurchase',
            name='feature_key',
            field=models.CharField(
                choices=[
                    ('attendance', 'Attendance'),
                    ('accounting', 'Accounting'),
                    ('cloud_storage', 'Cloud Storage'),
                ],
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name='carwashfeaturepurchase',
            name='payment_plan',
            field=models.CharField(
                choices=[
                    ('manual', 'Manual'),
                    ('cash', 'Cash'),
                    ('installment', 'Installment'),
                ],
                default='manual',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='carwashfeaturepurchase',
            name='total_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='carwashfeaturepurchase',
            name='paid_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='carwashfeaturepurchase',
            name='remaining_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='carwashfeaturepurchase',
            name='installment_months',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='carwashfeaturepurchase',
            name='monthly_installment_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='carwashfeaturepurchase',
            name='next_installment_due_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
