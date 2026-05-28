from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.inventory.models import InventoryItem
from apps.products.models import Product, ProductCategory


class Command(BaseCommand):
    help = 'Create default product categories, products and inventory stock'

    def handle(self, *args, **options):
        categories = [
            {'name': 'شوینده‌ها', 'slug': 'detergents', 'display_order': 1},
            {'name': 'لوازم مصرفی', 'slug': 'consumables', 'display_order': 2},
            {'name': 'نوشیدنی', 'slug': 'beverages', 'display_order': 3},
        ]

        category_by_slug = {}
        for item in categories:
            category, _ = ProductCategory.objects.update_or_create(
                slug=item['slug'],
                defaults={
                    'name': item['name'],
                    'display_order': item['display_order'],
                    'is_active': True,
                },
            )
            category_by_slug[item['slug']] = category

        products = [
            {
                'name': 'شامپو بدنه خودرو',
                'sku': 'CW-SH-001',
                'unit': 'عدد',
                'sale_price': Decimal('180000'),
                'cost_price': Decimal('130000'),
                'min_stock': 5,
                'category_slug': 'detergents',
                'stock_qty': Decimal('40'),
            },
            {
                'name': 'واکس داشبورد',
                'sku': 'CW-WX-002',
                'unit': 'عدد',
                'sale_price': Decimal('250000'),
                'cost_price': Decimal('190000'),
                'min_stock': 5,
                'category_slug': 'detergents',
                'stock_qty': Decimal('30'),
            },
            {
                'name': 'اسفنج شستشو',
                'sku': 'CW-SP-003',
                'unit': 'عدد',
                'sale_price': Decimal('90000'),
                'cost_price': Decimal('60000'),
                'min_stock': 10,
                'category_slug': 'consumables',
                'stock_qty': Decimal('80'),
            },
            {
                'name': 'دستمال مایکروفایبر',
                'sku': 'CW-MF-004',
                'unit': 'عدد',
                'sale_price': Decimal('70000'),
                'cost_price': Decimal('45000'),
                'min_stock': 20,
                'category_slug': 'consumables',
                'stock_qty': Decimal('120'),
            },
            {
                'name': 'نوشابه قوطی',
                'sku': 'CW-DR-005',
                'unit': 'عدد',
                'sale_price': Decimal('35000'),
                'cost_price': Decimal('25000'),
                'min_stock': 24,
                'category_slug': 'beverages',
                'stock_qty': Decimal('96'),
            },
            {
                'name': 'آب معدنی',
                'sku': 'CW-DR-006',
                'unit': 'عدد',
                'sale_price': Decimal('12000'),
                'cost_price': Decimal('8000'),
                'min_stock': 24,
                'category_slug': 'beverages',
                'stock_qty': Decimal('200'),
            },
        ]

        for item in products:
            category = category_by_slug[item['category_slug']]
            product, _ = Product.objects.update_or_create(
                sku=item['sku'],
                defaults={
                    'name': item['name'],
                    'category': category,
                    'unit': item['unit'],
                    'sale_price': item['sale_price'],
                    'cost_price': item['cost_price'],
                    'min_stock': item['min_stock'],
                    'is_active': True,
                },
            )

            InventoryItem.objects.update_or_create(
                product=product,
                defaults={
                    'quantity_on_hand': item['stock_qty'],
                    'reserved_quantity': Decimal('0'),
                    'min_quantity_alert': Decimal(str(item['min_stock'])),
                    'location': 'انبار اصلی',
                },
            )

        self.stdout.write(self.style.SUCCESS('Default products and inventory seeded successfully.'))

