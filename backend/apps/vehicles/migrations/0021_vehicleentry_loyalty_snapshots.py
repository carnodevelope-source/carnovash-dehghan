from decimal import Decimal

from django.db import migrations, models


HALF_STAR = Decimal('0.5')
MAX_STARS = Decimal('5.0')
CYCLE_VISIT_LIMIT = 10


def _visit_score_for_count(visit_count):
    number = int(visit_count or 0)
    if number <= 0:
        return Decimal('0')
    position = ((number - 1) % CYCLE_VISIT_LIMIT) + 1
    earned = HALF_STAR * Decimal(str(position))
    if earned > MAX_STARS:
        earned = MAX_STARS
    return earned


def backfill_loyalty_snapshots(apps, schema_editor):
    VehicleEntry = apps.get_model('vehicles', 'VehicleEntry')
    qs = (
        VehicleEntry.objects.filter(loyalty_score_snapshot__isnull=True)
        .exclude(status='cancelled')
        .order_by('tenant_id', 'plate_number', 'check_in_at', 'id')
    )
    counters = {}
    batch = []
    for vehicle in qs.iterator(chunk_size=500):
        if vehicle.is_piece_wash:
            vehicle.loyalty_score_snapshot = Decimal('0')
            vehicle.loyalty_visit_count_snapshot = 0
            vehicle.loyalty_discount_percent_snapshot = Decimal('0')
            batch.append(vehicle)
            continue
        key = (vehicle.tenant_id, str(vehicle.plate_number or '').strip())
        counters[key] = int(counters.get(key, 0) or 0) + 1
        visit_count = counters[key]
        vehicle.loyalty_visit_count_snapshot = visit_count
        vehicle.loyalty_score_snapshot = _visit_score_for_count(visit_count)
        # Percent is recomputed at read-time from score/visit when snapshot percent is null;
        # keep null here so current settings still apply for legacy rows if needed.
        batch.append(vehicle)
        if len(batch) >= 500:
            VehicleEntry.objects.bulk_update(
                batch,
                ['loyalty_score_snapshot', 'loyalty_visit_count_snapshot', 'loyalty_discount_percent_snapshot'],
            )
            batch = []
    if batch:
        VehicleEntry.objects.bulk_update(
            batch,
            ['loyalty_score_snapshot', 'loyalty_visit_count_snapshot', 'loyalty_discount_percent_snapshot'],
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('vehicles', '0020_expand_tariff_type_choices'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehicleentry',
            name='loyalty_score_snapshot',
            field=models.DecimalField(blank=True, decimal_places=1, max_digits=3, null=True),
        ),
        migrations.AddField(
            model_name='vehicleentry',
            name='loyalty_visit_count_snapshot',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='vehicleentry',
            name='loyalty_discount_percent_snapshot',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True),
        ),
        migrations.RunPython(backfill_loyalty_snapshots, noop_reverse),
    ]
