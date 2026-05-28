from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.workers.models import WorkerProfile


class Command(BaseCommand):
    help = 'Create default workers and related worker profiles'

    def handle(self, *args, **options):
        user_model = get_user_model()

        workers = [
            {
                'username': 'worker1',
                'password': 'worker123',
                'full_name': 'محمد رضایی',
                'phone': '09120000101',
                'role': 'worker',
                'profile': {
                    'code': 'W-001',
                    'default_commission_percent': 40,
                    'is_available': True,
                    'load_status': 'free',
                    'active_jobs_count': 0,
                    'notes': 'متخصص دیتیلینگ',
                },
            },
            {
                'username': 'worker2',
                'password': 'worker123',
                'full_name': 'سعید کریمی',
                'phone': '09120000102',
                'role': 'worker',
                'profile': {
                    'code': 'W-002',
                    'default_commission_percent': 35,
                    'is_available': False,
                    'load_status': 'busy',
                    'active_jobs_count': 2,
                    'notes': 'کارگر ساده',
                },
            },
        ]

        for item in workers:
            user, _ = user_model.objects.get_or_create(
                username=item['username'],
                defaults={
                    'full_name': item['full_name'],
                    'phone': item['phone'],
                    'role': item['role'],
                    'is_active': True,
                    'is_staff': False,
                    'is_superuser': False,
                },
            )

            user.full_name = item['full_name']
            user.phone = item['phone']
            user.role = item['role']
            user.is_active = True
            user.set_password(item['password'])
            user.save(update_fields=['full_name', 'phone', 'role', 'is_active', 'password'])

            profile_defaults = item['profile']
            WorkerProfile.objects.update_or_create(
                user=user,
                defaults=profile_defaults,
            )

        self.stdout.write(self.style.SUCCESS('Default workers seeded successfully.'))
