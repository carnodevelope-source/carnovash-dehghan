from django.db import migrations, models


def backfill_vehicle_payment_method(apps, schema_editor):
    VehicleEntry = apps.get_model('vehicles', 'VehicleEntry')
    Payment = apps.get_model('payments', 'Payment')

    latest_payments = (
        Payment.objects.exclude(method='')
        .order_by('vehicle_entry_id', '-created_at', '-id')
    )
    seen_vehicle_ids = set()
    for payment in latest_payments.iterator():
        vehicle_id = payment.vehicle_entry_id
        if not vehicle_id or vehicle_id in seen_vehicle_ids:
            continue
        seen_vehicle_ids.add(vehicle_id)
        VehicleEntry.objects.filter(id=vehicle_id).update(payment_method=payment.method)


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0006_payment_cheque_details'),
        ('vehicles', '0011_vehicleentry_is_piece_wash_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehicleentry',
            name='payment_method',
            field=models.CharField(blank=True, choices=[('pos', 'POS'), ('cash', 'Cash'), ('transfer', 'Transfer'), ('cheque', 'Cheque'), ('credit', 'Credit'), ('manual', 'Manual')], default='', max_length=20),
        ),
        migrations.AddIndex(
            model_name='vehicleentry',
            index=models.Index(fields=['payment_method', 'check_in_at'], name='vehicles_ve_payment_5cc23d_idx'),
        ),
        migrations.RunPython(backfill_vehicle_payment_method, migrations.RunPython.noop),
    ]
