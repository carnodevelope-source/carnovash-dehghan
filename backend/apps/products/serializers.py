from rest_framework import serializers
from django.utils.text import slugify

from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    available_quantity = serializers.SerializerMethodField()

    def get_available_quantity(self, obj):
        try:
            inventory = obj.inventory_item
        except Exception:
            return 0
        if inventory is None:
            return 0
        try:
            return float(getattr(inventory, 'available_quantity', 0) or 0)
        except (TypeError, ValueError):
            return 0

    def _generate_unique_sku(self, seed='prd'):
        base = (slugify(seed or '') or 'prd').upper().replace('-', '')
        base = base[:20] or 'PRD'
        candidate = base
        suffix = 1
        while Product.objects.filter(sku=candidate).exclude(pk=getattr(self.instance, 'pk', None)).exists():
            suffix += 1
            candidate = f'{base}-{suffix}'
        return candidate[:60]

    def validate_sku(self, value):
        value = (value or '').strip()
        if value:
            return value
        name_seed = self.initial_data.get('name') if isinstance(self.initial_data, dict) else ''
        return self._generate_unique_sku(name_seed or 'prd')

    def create(self, validated_data):
        sku = (validated_data.get('sku') or '').strip()
        if not sku:
            validated_data['sku'] = self._generate_unique_sku(validated_data.get('name', 'prd'))
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'sku' in validated_data:
            incoming = (validated_data.get('sku') or '').strip()
            validated_data['sku'] = incoming or instance.sku or self._generate_unique_sku(validated_data.get('name', instance.name))
        return super().update(instance, validated_data)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'sku', 'barcode', 'unit', 'description', 'sale_price', 'cost_price',
            'min_stock', 'is_active', 'available_quantity', 'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'sku': {'required': False, 'allow_blank': True},
        }
