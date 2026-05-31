from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.auth.models import CarWash


class Command(BaseCommand):
    help = 'Create default operator user: op/op123'

    def handle(self, *args, **options):
        user_model = get_user_model()
        tenant, _ = CarWash.objects.get_or_create(slug='default', defaults={'name': 'Default CarWash'})
        username = 'op'
        password = 'op123'

        user, created = user_model.objects.get_or_create(
            username=username,
            defaults={
                'full_name': 'Operator User',
                'phone': '09120000999',
                'tenant': tenant,
                'role': 'operator',
                'is_active': True,
                'is_staff': False,
                'is_superuser': False,
            },
        )

        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS('Operator user created: op / op123'))
        else:
            user.role = 'operator'
            user.is_active = True
            user.set_password(password)
            user.save(update_fields=['role', 'is_active', 'password'])
            self.stdout.write(self.style.WARNING('Operator user updated/reset: op / op123'))
