from django.contrib.auth import get_user_model
from apps.auth.models import CarWash


SEED_USERS = [
    {
        'username': 'admin',
        'password': 'Admin@12345',
        'full_name': 'Admin User',
        'phone': '09120000000',
        'role': 'admin',
        'is_staff': True,
        'is_superuser': True,
    },
    {
        'username': 'owner',
        'password': 'Owner@12345',
        'full_name': 'Owner User',
        'phone': '09120000001',
        'role': 'owner',
        'is_staff': True,
        'is_superuser': True,
    },
    {
        'username': 'manager',
        'password': 'Manager@12345',
        'full_name': 'Manager User',
        'phone': '09120000002',
        'role': 'manager',
        'is_staff': True,
        'is_superuser': False,
    },
    {
        'username': 'accountant',
        'password': 'Accountant@12345',
        'full_name': 'Accountant User',
        'phone': '09120000004',
        'role': 'accountant',
        'is_staff': False,
        'is_superuser': False,
    },
    {
        'username': 'operator',
        'password': 'Operator@12345',
        'full_name': 'Operator User',
        'phone': '09120000003',
        'role': 'operator',
        'is_staff': False,
        'is_superuser': False,
    },
]


def seed_users():
    user_model = get_user_model()
    tenant, _ = CarWash.objects.get_or_create(slug='default', defaults={'name': 'Default CarWash'})
    for item in SEED_USERS:
        username = item['username']
        defaults = {
            'full_name': item['full_name'],
            'phone': item['phone'],
            'tenant': tenant,
            'role': item['role'],
            'is_staff': item['is_staff'],
            'is_superuser': item['is_superuser'],
            'is_active': True,
        }
        user, created = user_model.objects.get_or_create(username=username, defaults=defaults)
        if created:
            user.set_password(item['password'])
            user.save()
