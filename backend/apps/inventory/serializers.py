from datetime import datetime, time

from rest_framework import serializers
from django.utils import timezone

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
    attachment = serializers.FileField(required=False, allow_null=True)
    attachment_url = serializers.SerializerMethodField()
    attachment_name = serializers.SerializerMethodField()
    spent_at = serializers.DateTimeField(required=False, allow_null=True, input_formats=['%Y-%m-%d', 'iso-8601'], format='%Y-%m-%d')

    class Meta:
        model = ExpenseEntry
        fields = [
            'id',
            'title',
            'amount',
            'details',
            'attachment',
            'attachment_url',
            'attachment_name',
            'source_type',
            'spent_at',
            'created_at',
            'updated_at',
            'created_by_name',
        ]
        read_only_fields = ['source_type', 'created_at', 'updated_at', 'created_by_name', 'attachment_url', 'attachment_name']

    def get_created_by_name(self, obj):
        if not obj.created_by:
            return '-'
        return obj.created_by.full_name or obj.created_by.username

    def get_attachment_url(self, obj):
        if not obj.attachment:
            return ''
        request = self.context.get('request')
        url = obj.attachment.url
        return request.build_absolute_uri(url) if request else url

    def get_attachment_name(self, obj):
        if obj.attachment_original_name:
            return obj.attachment_original_name
        if not obj.attachment:
            return ''
        return str(obj.attachment.name).split('/')[-1]

    def _normalize_spent_at(self, spent_at):
        if spent_at is None:
            return None
        dt = datetime.combine(spent_at, time.min)
        return timezone.make_aware(dt) if timezone.is_naive(dt) else dt

    def create(self, validated_data):
        spent_at = validated_data.pop('spent_at', None)
        attachment = validated_data.get('attachment')
        if attachment and not validated_data.get('attachment_original_name'):
            validated_data['attachment_original_name'] = getattr(attachment, 'name', '')
        if spent_at is not None:
            validated_data['spent_at'] = self._normalize_spent_at(spent_at)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        spent_at = validated_data.pop('spent_at', None)
        attachment = validated_data.get('attachment')
        if attachment and not validated_data.get('attachment_original_name'):
            validated_data['attachment_original_name'] = getattr(attachment, 'name', '')
        if spent_at is not None:
            validated_data['spent_at'] = self._normalize_spent_at(spent_at)
        return super().update(instance, validated_data)
