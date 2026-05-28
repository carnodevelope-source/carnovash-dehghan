from django.core.management.base import BaseCommand

from apps.auth.management_seed import seed_users


class Command(BaseCommand):
    help = 'Seed default users (admin/owner/manager/accountant/operator)'

    def handle(self, *args, **options):
        seed_users()
        self.stdout.write(self.style.SUCCESS('Default users seeded successfully.'))
