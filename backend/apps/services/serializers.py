from decimal import Decimal

from rest_framework import serializers

from .models import GeneralSettings, Service, ServiceChangeLog


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
    def validate_discount_percent_per_half_star(self, value):
        if value < Decimal('0') or value > Decimal('100'):
            raise serializers.ValidationError('درصد تخفیف باید بین ۰ تا ۱۰۰ باشد.')
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
            'receipt_footer_note',
        ]:
            if key in attrs:
                attrs[key] = str(attrs.get(key) or '').strip()
        return attrs

    class Meta:
        model = GeneralSettings
        fields = [
            'id',
            'discount_percent_per_half_star',
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
            'receipt_footer_note',
            'created_at',
            'updated_at',
        ]
