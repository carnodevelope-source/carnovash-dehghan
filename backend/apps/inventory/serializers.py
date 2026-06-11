from rest_framework import serializers

from .models import ExpenseEntry, InventoryItem, StockMovement


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


class StockMovementHistorySerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source='inventory_item.product_id', read_only=True)
    product_name = serializers.CharField(source='inventory_item.product.name', read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = StockMovement
        fields = [
            'id',
            'product_id',
            'product_name',
            'movement_type',
            'quantity',
            'unit_cost',
            'sale_price_snapshot',
            'note',
            'reference_type',
            'moved_at',
            'created_by_name',
        ]

    def get_created_by_name(self, obj):
        if not obj.created_by:
            return '-'
        return obj.created_by.full_name or obj.created_by.username


class ExpenseEntrySerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ExpenseEntry
        fields = [
            'id',
            'title',
            'amount',
            'details',
            'source_type',
            'spent_at',
            'created_at',
            'updated_at',
            'created_by_name',
        ]
        read_only_fields = ['source_type', 'spent_at', 'created_at', 'updated_at', 'created_by_name']

    def get_created_by_name(self, obj):
        if not obj.created_by:
            return '-'
        return obj.created_by.full_name or obj.created_by.username
