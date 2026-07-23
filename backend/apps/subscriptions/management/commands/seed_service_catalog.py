from django.core.management.base import BaseCommand

from apps.subscriptions.services import backfill_subscriptions_from_feature_purchases, seed_catalog_from_legacy


class Command(BaseCommand):
    help = 'Seed service catalog and backfill subscriptions from CarWashFeaturePurchase.'

    def add_arguments(self, parser):
        parser.add_argument('--backfill', action='store_true', help='Also backfill from feature purchases')

    def handle(self, *args, **options):
        project = seed_catalog_from_legacy()
        self.stdout.write(self.style.SUCCESS(f'Catalog seeded for project {project.code}'))
        if options.get('backfill'):
            created = backfill_subscriptions_from_feature_purchases()
            self.stdout.write(self.style.SUCCESS(f'Backfilled {created} subscriptions'))
