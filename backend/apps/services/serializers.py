from decimal import Decimal

from rest_framework import serializers

from .models import GeneralSettings, Service


class ServiceSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Service
        fields = [
            'id',
            'name',
            'code',
            'description',
            'category',
            'category_name',
            'base_price',
            'pricing_mode',
            'estimated_duration_minutes',
            'allow_price_override',
            'is_active',
            'display_order',
            'created_at',
            'updated_at',
        ]


class GeneralSettingsSerializer(serializers.ModelSerializer):
    def validate_discount_percent_per_half_star(self, value):
        if value < Decimal('0') or value > Decimal('100'):
            raise serializers.ValidationError('درصد تخفیف باید بین ۰ تا ۱۰۰ باشد.')
        return value

    class Meta:
        model = GeneralSettings
        fields = [
            'id',
            'discount_percent_per_half_star',
            'created_at',
            'updated_at',
        ]
