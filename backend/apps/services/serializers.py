from django.conf import settings
from decimal import Decimal

from rest_framework import serializers

from .models import (
    CAR_SERVICE_TIER_KEYS,
    MOTORCYCLE_SERVICE_TIER_KEYS,
    GeneralSettings,
    Service,
    ServiceChangeLog,
    default_service_tiers,
    normalize_vehicle_assigned_sms_template,
    normalize_vehicle_released_sms_template,
)
from apps.vehicles.loyalty import normalize_fixed_visit_discounts


class ServiceSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    resolved_tariff_type = serializers.SerializerMethodField()
    resolved_list_price = serializers.SerializerMethodField()
    resolved_sale_price = serializers.SerializerMethodField()
    resolved_duration_minutes = serializers.SerializerMethodField()

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
            'pricing_tiers',
            'motorcycle_enabled',
            'motorcycle_pricing_tiers',
            'resolved_tariff_type',
            'resolved_list_price',
            'resolved_sale_price',
            'resolved_duration_minutes',
            'allow_price_override',
            'is_active',
            'display_order',
            'created_at',
            'updated_at',
        ]

    def _request_plate_type(self):
        request = self.context.get('request')
        raw_value = ''
        if request:
            raw_value = request.query_params.get('plate_type', '')
        return 'motorcycle' if str(raw_value or '').strip().lower() == 'motorcycle' else 'car'

    def _request_tariff_type(self):
        request = self.context.get('request')
        raw_value = ''
        if request:
            raw_value = request.query_params.get('tariff_type', '')
        fallback = 'type_1'
        return str(raw_value or fallback).strip().lower() or fallback

    def _resolved_pricing(self, obj):
        return obj.resolve_pricing(
            tariff_type=self._request_tariff_type(),
            plate_type=self._request_plate_type(),
        )

    def get_resolved_tariff_type(self, obj):
        return self._resolved_pricing(obj)['tariff_type']

    def get_resolved_list_price(self, obj):
        return self._resolved_pricing(obj)['list_price']

    def get_resolved_sale_price(self, obj):
        return self._resolved_pricing(obj)['sale_price']

    def get_resolved_duration_minutes(self, obj):
        return self._resolved_pricing(obj)['duration_minutes']

    def _normalize_tiers(self, raw_value, *, keys, sale_price, duration_minutes):
        defaults = default_service_tiers(keys, sale_price=sale_price, duration_minutes=duration_minutes)
        source = raw_value if isinstance(raw_value, dict) else {}
        normalized = {}
        for key in keys:
            current = source.get(key, {}) if isinstance(source.get(key, {}), dict) else {}
            list_price = Decimal(str(current.get('list_price', defaults[key]['list_price']) or 0))
            sale_price_value = Decimal(str(current.get('sale_price', defaults[key]['sale_price']) or 0))
            duration_value = int(current.get('duration_minutes', defaults[key]['duration_minutes']) or defaults[key]['duration_minutes'])
            if list_price < 0 or sale_price_value < 0:
                raise serializers.ValidationError('مبالغ هر تیپ نمی‌توانند منفی باشند.')
            if duration_value < 1:
                raise serializers.ValidationError('زمان هر تیپ باید حداقل ۱ دقیقه باشد.')
            normalized[key] = {
                'list_price': float(list_price),
                'sale_price': float(sale_price_value),
                'duration_minutes': duration_value,
            }
        return normalized

    def validate(self, attrs):
        attrs = super().validate(attrs)
        base_price = Decimal(str(attrs.get('base_price', getattr(self.instance, 'base_price', 0)) or 0))
        estimated_duration_minutes = int(attrs.get('estimated_duration_minutes', getattr(self.instance, 'estimated_duration_minutes', 30)) or 30)
        motorcycle_enabled = bool(attrs.get('motorcycle_enabled', getattr(self.instance, 'motorcycle_enabled', False)))

        attrs['pricing_tiers'] = self._normalize_tiers(
            attrs.get('pricing_tiers', getattr(self.instance, 'pricing_tiers', {})),
            keys=CAR_SERVICE_TIER_KEYS,
            sale_price=base_price,
            duration_minutes=estimated_duration_minutes,
        )
        attrs['motorcycle_pricing_tiers'] = self._normalize_tiers(
            attrs.get('motorcycle_pricing_tiers', getattr(self.instance, 'motorcycle_pricing_tiers', {})),
            keys=MOTORCYCLE_SERVICE_TIER_KEYS,
            sale_price=base_price,
            duration_minutes=estimated_duration_minutes,
        ) if motorcycle_enabled else {}

        primary_tier = attrs['pricing_tiers'].get('type_1', {})
        attrs['base_price'] = Decimal(str(primary_tier.get('sale_price', base_price) or 0))
        attrs['estimated_duration_minutes'] = int(primary_tier.get('duration_minutes', estimated_duration_minutes) or estimated_duration_minutes)
        return attrs


class ServiceChangeLogSerializer(serializers.ModelSerializer):
    changed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ServiceChangeLog
        fields = [
            'id',
            'action_type',
            'changed_by_name',
            'name_snapshot',
            'base_price_snapshot',
            'estimated_duration_snapshot',
            'is_active_snapshot',
            'change_summary',
            'created_at',
        ]

    def get_changed_by_name(self, obj):
        if not obj.changed_by:
            return '-'
        return obj.changed_by.full_name or obj.changed_by.username


class GeneralSettingsSerializer(serializers.ModelSerializer):
    sms_provider_api_key_configured = serializers.SerializerMethodField(read_only=True)
    sms_provider_source = serializers.SerializerMethodField(read_only=True)

    def validate_discount_percent_per_half_star(self, value):
        if value < Decimal('0') or value > Decimal('100'):
            raise serializers.ValidationError('درصد تخفیف باید بین ۰ تا ۱۰۰ باشد.')
        return value

    def validate_discount_calculation_mode(self, value):
        normalized = str(value or GeneralSettings.DiscountCalculationMode.STEP).strip().lower()
        if normalized not in {choice[0] for choice in GeneralSettings.DiscountCalculationMode.choices}:
            raise serializers.ValidationError('شیوه محاسبه تخفیف معتبر نیست.')
        return normalized

    def validate_fixed_visit_discounts(self, value):
        return normalize_fixed_visit_discounts(value)

    def validate_tax_percent(self, value):
        if value < Decimal('0') or value > Decimal('100'):
            raise serializers.ValidationError('درصد مالیات باید بین ۰ تا ۱۰۰ باشد.')
        return value

    def validate_bank_card_number(self, value):
        digits = ''.join(ch for ch in str(value or '') if ch.isdigit())
        if digits and len(digits) not in {16, 19}:
            raise serializers.ValidationError('شماره کارت باید ۱۶ رقم باشد.')
        return digits

    def validate_bank_account_iban(self, value):
        iban = str(value or '').strip().upper().replace(' ', '')
        if iban and not iban.startswith('IR'):
            iban = f'IR{iban}'
        if iban and len(iban) != 26:
            raise serializers.ValidationError('شبا باید ۲۶ کاراکتر باشد.')
        return iban

    def validate_receipt_printer_paper_width(self, value):
        normalized = str(value or '').strip().lower()
        if normalized and normalized not in {'58mm', '80mm', 'a4'}:
            raise serializers.ValidationError('عرض کاغذ باید یکی از 58mm، 80mm یا A4 باشد.')
        return normalized or '80mm'

    def validate_receipt_print_copies(self, value):
        copies = int(value or 1)
        if copies < 1 or copies > 5:
            raise serializers.ValidationError('تعداد نسخه باید بین ۱ تا ۵ باشد.')
        return copies

    def validate(self, attrs):
        for key in [
            'preferred_bank_name',
            'bank_account_holder',
            'pos_device_name',
            'pos_terminal_id',
            'payment_methods_note',
            'receipt_printer_name',
            'receipt_header_note',
            'receipt_footer_note',
            'sms_vehicle_assigned_template',
            'sms_vehicle_assigned_invoice_template',
            'sms_vehicle_released_template',
        ]:
            if key in attrs:
                attrs[key] = str(attrs.get(key) or '').strip()
        if 'sms_vehicle_released_template' in attrs:
            attrs['sms_vehicle_released_template'] = normalize_vehicle_released_sms_template(
                attrs.get('sms_vehicle_released_template')
            )
        if 'sms_vehicle_assigned_template' in attrs:
            attrs['sms_vehicle_assigned_template'] = normalize_vehicle_assigned_sms_template(
                attrs.get('sms_vehicle_assigned_template')
            )
        return attrs

    def get_sms_provider_api_key_configured(self, _obj):
        return bool(str(getattr(settings, 'IRANPAYAMAK_API_KEY', '') or '').strip())

    def get_sms_provider_source(self, _obj):
        return 'env'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['sms_provider_base_url'] = str(
            getattr(settings, 'IRANPAYAMAK_BASE_URL', 'https://api.iranpayamak.com')
            or 'https://api.iranpayamak.com'
        ).rstrip('/')
        data['sms_provider_line_number'] = str(getattr(settings, 'IRANPAYAMAK_LINE_NUMBER', '') or '').strip()
        data['sms_provider_api_key'] = ''
        return data

    class Meta:
        model = GeneralSettings
        fields = [
            'id',
            'discount_percent_per_half_star',
            'discount_calculation_mode',
            'fixed_visit_discounts',
            'tax_enabled',
            'tax_percent',
            'preferred_bank_name',
            'bank_account_holder',
            'bank_card_number',
            'bank_account_iban',
            'pos_device_name',
            'pos_terminal_id',
            'payment_methods_note',
            'receipt_printer_enabled',
            'receipt_printer_name',
            'receipt_printer_paper_width',
            'receipt_print_copies',
            'receipt_auto_print',
            'receipt_show_logo',
            'receipt_show_qr',
            'receipt_header_note',
            'receipt_footer_note',
            'sms_provider_base_url',
            'sms_provider_api_key',
            'sms_provider_line_number',
            'sms_provider_api_key_configured',
            'sms_provider_source',
            'sms_vehicle_auto_send_enabled',
            'sms_vehicle_assigned_enabled',
            'sms_vehicle_assigned_invoice_enabled',
            'sms_vehicle_released_enabled',
            'sms_vehicle_assigned_template',
            'sms_vehicle_assigned_invoice_template',
            'sms_vehicle_released_template',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'sms_provider_base_url',
            'sms_provider_api_key',
            'sms_provider_line_number',
            'sms_provider_api_key_configured',
            'sms_provider_source',
        ]
