from django.db import migrations, models


def forwards(apps, schema_editor):
    WorkerProfile = apps.get_model('workers', 'WorkerProfile')
    for profile in WorkerProfile.objects.all():
        items = []
        if profile.has_entrusted_item and str(profile.entrusted_item_description or '').strip():
            items.append({
                'title': str(profile.entrusted_item_description or '').strip(),
                'quantity': float(profile.entrusted_item_quantity or 0),
                'price': float(profile.entrusted_item_price or 0),
            })
        profile.entrusted_items = items
        profile.save(update_fields=['entrusted_items'])


def backwards(apps, schema_editor):
    WorkerProfile = apps.get_model('workers', 'WorkerProfile')
    for profile in WorkerProfile.objects.all():
        items = profile.entrusted_items if isinstance(profile.entrusted_items, list) else []
        first = items[0] if items else {}
        profile.has_entrusted_item = bool(items)
        profile.entrusted_item_description = str(first.get('title') or '').strip()
        profile.entrusted_item_quantity = first.get('quantity') or 0
        profile.entrusted_item_price = first.get('price') or 0
        profile.save(update_fields=['has_entrusted_item', 'entrusted_item_description', 'entrusted_item_quantity', 'entrusted_item_price'])


class Migration(migrations.Migration):

    dependencies = [
        ('workers', '0005_merge_20260606_1917'),
    ]

    operations = [
        migrations.AddField(
            model_name='workerprofile',
            name='entrusted_items',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.RunPython(forwards, backwards),
    ]
