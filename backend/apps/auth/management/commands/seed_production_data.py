from django.core.management.base import BaseCommand

from apps.auth.production_seed import seed_production_data


class Command(BaseCommand):
    help = "Seed production tenants, feature flags, and login accounts."

    def handle(self, *args, **options):
        seed_production_data()
        self.stdout.write(self.style.SUCCESS("Production bootstrap data seeded successfully."))
