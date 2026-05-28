from rest_framework import serializers

from .models import InventoryItem


class InventoryItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    available_quantity = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = InventoryItem
        fields = [
            'id',
            'product',
            'product_name',
            'product_sku',
            'quantity_on_hand',
            'reserved_quantity',
            'available_quantity',
            'min_quantity_alert',
            'location',
            'created_at',
            'updated_at',
        ]
