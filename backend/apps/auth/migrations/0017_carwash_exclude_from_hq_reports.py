from django.db import migrations, models
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.utils import timezone


TEST_MANAGER_PHONES = {
    '09134550268',
    '09120001001',
    '08888888888',
}
TEST_SLUGS = {
    'carwash-1',
}
PERSIAN_DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')


def _normalize(value):
    text = str(value or '').translate(PERSIAN_DIGITS)
    text = text.replace('\u200c', ' ').replace('*', '')
    return ' '.join(text.split())


def _is_test_tenant(tenant, manager_phones):
    name = _normalize(getattr(tenant, 'name', ''))
    slug = _normalize(getattr(tenant, 'slug', '')).lower()
    address = _normalize(getattr(tenant, 'address', ''))
    if slug in TEST_SLUGS:
        return True
    if name.startswith('تست 1'):
        return True
    if name == 'کارواش یک' and (address == 'تهران' or manager_phones & TEST_MANAGER_PHONES):
        return True
    return False


def mark_internal_and_cleanup_test_carwashes(apps, schema_editor):
    CarWash = apps.get_model('cw_auth', 'CarWash')
    User = apps.get_model('cw_auth', 'User')

    CarWash.objects.filter(
        Q(name__icontains='میلان') | Q(slug__icontains='milan')
    ).update(exclude_from_hq_reports=True)

    tenant_ids = set(
        User.objects.filter(phone__in=TEST_MANAGER_PHONES, tenant_id__isnull=False)
        .values_list('tenant_id', flat=True)
    )
    for tenant in CarWash.objects.all().only('id', 'name', 'slug', 'address'):
        manager_phones = set(User.objects.filter(tenant_id=tenant.id).values_list('phone', flat=True))
        if _is_test_tenant(tenant, manager_phones):
            tenant_ids.add(tenant.id)

    now = timezone.now()
    for tenant in CarWash.objects.filter(id__in=tenant_ids):
        try:
            User.objects.filter(tenant_id=tenant.id).delete()
            tenant.delete()
        except ProtectedError:
            User.objects.filter(tenant_id=tenant.id).update(
                is_active=False,
                is_deleted=True,
                deleted_at=now,
            )
            CarWash.objects.filter(pk=tenant.id).update(
                is_active=False,
                exclude_from_hq_reports=True,
                updated_at=now,
            )


class Migration(migrations.Migration):

    dependencies = [
        ('cw_auth', '0016_hq_platform_roles_expand'),
    ]

    operations = [
        migrations.AddField(
            model_name='carwash',
            name='exclude_from_hq_reports',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(mark_internal_and_cleanup_test_carwashes, migrations.RunPython.noop),
    ]
