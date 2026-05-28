from rest_framework import serializers

from .models import Service


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
