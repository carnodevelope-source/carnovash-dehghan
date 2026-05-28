from rest_framework import serializers

from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'sku', 'barcode', 'unit', 'sale_price', 'cost_price',
            'min_stock', 'is_active', 'created_at', 'updated_at'
        ]
